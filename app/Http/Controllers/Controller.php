<?php

namespace App\Http\Controllers;

use Illuminate\Foundation\Auth\Access\AuthorizesRequests;
use Illuminate\Foundation\Bus\DispatchesJobs;
use Illuminate\Foundation\Validation\ValidatesRequests;
use Illuminate\Routing\Controller as BaseController;

use FabianBeiner\Todoist\TodoistClient;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

use Jenssegers\Date\Date;

use Spatie\GoogleCalendar\Event;

class Controller extends BaseController
{
    use AuthorizesRequests, DispatchesJobs, ValidatesRequests;

    public function index()
    {

        $today = new Date('today');
        $refreshRate = env('REFRESH_RATE_IN_SECONDS',1800);

        // Get tasks from the API
        $Todoist = new TodoistClient(env('TODOIST_API_KEY'));
        $options = array(
            'filter' => env('TODOIST_FILTER','7 days | overdue') 
        );
        
        // Todoist API sometimes timeouts
        try {
            $elements = $Todoist->getAllTasks($options);
            Log::info("TODOIST API:Success in the first try");
        } catch (\Exception $e) {
            Log::error("TODOIST API:Problem in first try");
            report($e);
            try {
                $elements = $Todoist->getAllTasks($options);
                Log::warning("TODOIST API:Success in the second try");
            }catch (\Exception $etwo) {
                Log::error("TODOIST API:Problem in second try");
                report($e);
                $elements = array();
                // Force refresh in 15 seconds to restart the whole request
                $refreshRate = 15;
                }            
        }
        
        // Store todays date in Readable form: Sunday 12 december 2021
        $date = Date::now()->format(env('APP_DATE_HEADER_MASK','l j F Y'));       

        // This collection will contain tasks (Todoist) and events (Google Calendar)
        $filteredElements = collect();

        //********************************************************************************************************************************/
        //***************************************TODOIST TASKS PROCESSING*****************************************************************/
        //********************************************************************************************************************************/
        foreach ($elements as $element){           

            // Filter tasks removing links (it makes the task too long for the kindle screen)
            $content = preg_replace('/\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|$!:,.;]*[A-Z0-9+&@#\/%=~_|$]/i', '', $element['content']);

            if (strpos($content,']()') !== false ){
                // The ']()' string was found, so it was a link with text. Remove clutter
                $content = str_replace(']()',']',$content);
            }

            $elementAsCollection = collect();

            // If the task has hour and the setting is on, append [HH:MM] to the left of the title
            if (env('ADD_HOUR',True) & isset($element['due']['datetime'])){

                // Get datetime in a date object and apply the timezone
                $dateWithHour = new Date($element['due']['datetime']);
                $dateWithHour->setTimezone(env('APP_TIMEZONE','Europe/Madrid'));

                // // Add a '0' to avoid times like 9:15 (instead of 09:15) or 12:4 (instead of 12:04)
                $hourString = ($dateWithHour->hour < 10) ? '0' . strval($dateWithHour->hour) : strval($dateWithHour->hour);
                $minuteString = ($dateWithHour->minute < 10) ? '0' . strval($dateWithHour->minute) : strval($dateWithHour->minute);

                $elementAsCollection->put('hour',$hourString . ':' . $minuteString);
                // // Modify the task title
                // $content = '[' . $hourString . ':' . $minuteString . '] ' . $content;

            }else{
                /*Use '00:00' as hour in tasks without hour, as we want this tasks to appear before the ordered
                tasks with hour*/ 
                $elementAsCollection->put('hour','00:00'); 
            }

            // If task longer than ELEMENT_MAX_LENGHT, truncate it so it fits in Kindle Touch width
            $content = Str::of($content)->limit(env('ELEMENT_MAX_LENGHT',66));

            // Add the processed task to $filteredElements
            
            $elementAsCollection->put('date',$element['due']['date']);
            $elementAsCollection->put('title',$content);
            $elementAsCollection->put('type','task');
            $filteredElements->push($elementAsCollection);
        }


        //********************************************************************************************************************************/
        //***************************************GOOGLE CALENDAR EVENTS PROCESSING********************************************************/
        //********************************************************************************************************************************/
        if (env('GCAL_QUERY_EVENTS',True)){

            $limitDate = new Date('today');
            $limitDate->addDays(7);

            // Get all Google Calendars IDs
            $calendars = explode(',',env('GCAL_CALENDARS_IDS'));

            foreach($calendars as $calendar){

                // get all future events on a calendar
                try {
                    $events = Event::get($today,$limitDate,[],$calendar);
                    Log::info("GCAL API:Success in the first try");
                }catch (\Exception $e) {
                    Log::error("GCAL API:Problem in first try");
                    $events = Event::get($today,$limitDate,[],$calendar);
                    Log::warning("GCAL API:Success in the second try");
                }
                
        
                foreach ($events as $event){
                    $eventAsCollection = collect();
    
                    $title = $event->name;
                    // If event title longer than ELEMENT_MAX_LENGHT, truncate it so it fits in Kindle Touch width
                    $title = Str::of($title)->limit(env('ELEMENT_MAX_LENGHT',66));
    
                    $eventAsCollection->put('title',$title);
                    $eventAsCollection->put('date',$event->startDateTime->format('Y-m-d'));
                    $eventAsCollection->put('hour',$event->startDateTime->format('H:i'));
                    $eventAsCollection->put('type','event');
    
                    $filteredElements->push($eventAsCollection);
                }
            }
        }
              

        //********************************************************************************************************************************/
        //***************************************PROCESSING ELEMENTS INTO 4 FINAL COLLECTIONS*********************************************/
        //********************************************************************************************************************************/

        // Order the tasks by hour
        $filteredElements = $filteredElements->sortBy([
            ['hour', 'asc'],
        ]);
        $filteredElements = $filteredElements->values()->all();


        /* We're gonne pass four date-related collections to the view
        - overdueElements
        - todayElements
        - tomorrowElements
        - regularElements: (from the day after tomorrow to the end, in chronological order)
        
        We do it like that because we need to group overdue tasks in one element and building the
        HTML blocks is easier this wat
        */

        $overdueElements = collect();
        // Will have two keys: readableName and elements
        $overdueElements-> put('readableName',env('APP_LOCALE_OVERDUE','Overdue'));
        $overdueElements-> put('elements',collect());

        // Will have two keys: readableName and elements
        $todayElements = collect();
        $todayElements-> put('readableName',env('APP_LOCALE_TODAY','Today'));
        $todayElements-> put('elements',collect());

        // Will have two keys: readableName and elements
        $tomorrowElements = collect();
        $tomorrowElements-> put('readableName',env('APP_LOCALE_TOMORROW','Tomorrow'));
        $tomorrowElements-> put('elements',collect());

        // Will have a key for every date in the 'YYYY-MM-DD' format. 
        $regularElements = collect();

        foreach($filteredElements as $element){

            // If the task has hour, append it to the title
            $title = ($element->get('hour') === '00:00') ? $element->get('title') : '[' . $element->get('hour') . '] ' . $element->get('title');
            $type = $element->get('type');

            $elementDate = new Date($element->get('date'));

            if ($today->diffInHours($elementDate,false) < 0){
                
                // Overdue Task
                $elements = $overdueElements->get('elements');
                $newElement = collect();
                $newElement->put('title',$title);
                $newElement->put('type',$type);
                $elements->push($newElement);
                $overdueElements->put('elements',$elements);

            }else if ($elementDate->equalTo($today)){
           
                // Today Task
                $elements = $todayElements->get('elements');
                $newElement = collect();
                $newElement->put('title',$title);
                $newElement->put('type',$type);
                $elements->push($newElement);
                $todayElements->put('elements',$elements);

            }else if ($elementDate->diffInDays($today) == 1){
               
                // Tomorrow Task
                $elements = $tomorrowElements->get('elements');
                $newElement = collect();
                $newElement->put('title',$title);
                $newElement->put('type',$type);
                $elements->push($newElement);
                $tomorrowElements->put('elements',$elements);
            }else{
                
                // Regular task (> tomorrow)
                $readableDate = $elementDate->format(env('APP_LOCALE_OTHERS_MASK','l,j \de F'));
                
                if (!$regularElements->has($element->get('date'))){
                    //First task with this date, init the collection
                    $fields = collect();
                    $fields->put("readableDate",$readableDate);
                    
                    $newElement = collect();
                    $newElement->put('title',$title);
                    $newElement->put('type',$type);

                    $elementsArray = collect();
                    $elementsArray->push($newElement);

                    $fields->put("elements",$elementsArray);
                
                    $regularElements->put($element->get('date'),$fields);
                }else{
                    $fields = $regularElements->get($element->get('date'));
                    $elements = $fields->get('elements');

                    $newElement = collect();
                    $newElement->put('title',$title);
                    $newElement->put('type',$type);
                    $elements->push($newElement);
                    
                    $regularElements->merge($elements->get('date'),$fields);
                }
            }
        }

        $regularElements = $regularElements->sortKeys();

        log::debug($overdueElements);
        log::debug($todayElements);
        log::debug($tomorrowElements);
        log::debug($regularElements);

        return view('index',['date' => $date,'overdueElements' => $overdueElements, 'todayElements' => $todayElements, 'tomorrowElements' => $tomorrowElements,'regularElements' => $regularElements, 'refreshRate' => $refreshRate]);
    }
}
