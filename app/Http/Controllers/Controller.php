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
            $tasks = $Todoist->getAllTasks($options);
            Log::info("TODOIST API:Success in the first try");
        } catch (\Exception $e) {
            Log::error("TODOIST API:Problem in first try");
            report($e);
            try {
                $tasks = $Todoist->getAllTasks($options);
                Log::info("TODOIST API:Success in the second try");
            }catch (\Exception $etwo) {
                Log::error("TODOIST API:Problem in second try");
                report($e);
                $tasks = array();
                // Force refresh in 15 seconds to restart the whole request
                $refreshRate = 15;
                }            
        }
        
        // Store todays date in Readable form: Sunday 12 december 2021
        $date = Date::now()->format(env('APP_DATE_HEADER_MASK','l j F Y'));       

        $filteredtasks = collect();
        foreach ($tasks as $task){           

            // Filter tasks removing links (it makes the task too long for the kindle screen)
            $content = preg_replace('/\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|$!:,.;]*[A-Z0-9+&@#\/%=~_|$]/i', '', $task['content']);

            if (strpos($content,']()') !== false ){
                // The ']()' string was found, so it was a link with text. Remove clutter
                $content = str_replace(']()',']',$content);
            }

            $taskAsCollection = collect();

            // If the task has hour and the setting is on, append [HH:MM] to the left of the title
            if (env('ADD_HOUR',True) & isset($task['due']['datetime'])){

                // Get datetime in a date object and apply the timezone
                $dateWithHour = new Date($task['due']['datetime']);
                $dateWithHour->setTimezone(env('APP_TIMEZONE','Europe/Madrid'));

                // // Add a '0' to avoid times like 9:15 (instead of 09:15) or 12:4 (instead of 12:04)
                $hourString = ($dateWithHour->hour < 10) ? '0' . strval($dateWithHour->hour) : strval($dateWithHour->hour);
                $minuteString = ($dateWithHour->minute < 10) ? '0' . strval($dateWithHour->minute) : strval($dateWithHour->minute);

                $taskAsCollection->put('hour',$hourString . ':' . $minuteString);
                // // Modify the task title
                // $content = '[' . $hourString . ':' . $minuteString . '] ' . $content;

            }else{
                /*Use '00:00' as hour in tasks without hour, as we want this tasks to appear before the ordered
                tasks with hour*/ 
                $taskAsCollection->put('hour','00:00'); 
            }

            // If task longer than TASK_MAX_LENGHT, truncate it so it fits in Kindle Touch width
            $content = Str::of($content)->limit(env('TASK_MAX_LENGHT',66));

            // Add the processed task to $filteredtasks
            
            $taskAsCollection->put('date',$task['due']['date']);
            $taskAsCollection->put('title',$content);
            $filteredtasks->push($taskAsCollection);
        }

        $limitDate = new Date('today');
        $limitDate->addDays(7);
        //Log::debug($today);
        //Log::debug($limitDate);

        // get all future events on a calendar
        $events = Event::get($today,$limitDate);
        //Log::debug($events);

        foreach ($events as $event){
            $eventAsCollection = collect();

            $eventAsCollection->put('title',$event->name);
            $eventAsCollection->put('date',$event->startDateTime->format('Y-m-d'));
            $eventAsCollection->put('hour',$event->startDateTime->format('H:i'));

            $filteredtasks->push($eventAsCollection);

            // Log::debug($event->name);
            // Log::debug($event->startDateTime->format('Y-m-d'));
            // Log::debug($event->startDateTime->format('H:i'));
        }

        // Order the tasks by hour
        $filteredtasks = $filteredtasks->sortBy([
            ['hour', 'asc'],
        ]);
        $filteredtasks = $filteredtasks->values()->all();


        /* We're gonne pass four date-related collections to the view
        - overdueTasks
        - todayTasks
        - tomorrowTasks
        - regularTasks: (from the day after tomorrow to the end, in chronological order)
        
        We do it like that because we need to group overdue tasks in one element and building the
        HTML blocks is easier this wat
        */

        $overdueTasks = collect();
        // Will have two keys: readableName and tasks
        $overdueTasks-> put('readableName',env('APP_LOCALE_OVERDUE','Overdue'));
        $overdueTasks-> put('tasks',collect());

        // Will have two keys: readableName and tasks
        $todayTasks = collect();
        $todayTasks-> put('readableName',env('APP_LOCALE_TODAY','Today'));
        $todayTasks-> put('tasks',collect());

        // Will have two keys: readableName and tasks
        $tomorrowTasks = collect();
        $tomorrowTasks-> put('readableName',env('APP_LOCALE_TOMORROW','Tomorrow'));
        $tomorrowTasks-> put('tasks',collect());

        // Will have a key for every date in the 'YYYY-MM-DD' format. 
        $regularTasks = collect();

        foreach($filteredtasks as $task){

            // If the task has hour, append it to the title
            $title = ($task->get('hour') === '00:00') ? $task->get('title') : '[' . $task->get('hour') . '] ' . $task->get('title');

            $taskDate = new Date($task->get('date'));

            if ($today->diffInHours($taskDate,false) < 0){
                
                // Overdue Task
                $tasks = $overdueTasks->get('tasks');
                $tasks->push($title);
                $overdueTasks->put('tasks',$tasks);

            }else if ($taskDate->equalTo($today)){
           
                // Today Task
                $tasks = $todayTasks->get('tasks');
                $tasks->push($title);
                $todayTasks->put('tasks',$tasks);

            }else if ($taskDate->diffInDays($today) == 1){
               
                // Tomorrow Task
                $tasks = $tomorrowTasks->get('tasks');
                $tasks->push($title);
                $tomorrowTasks->put('tasks',$tasks);
            }else{
                
                // Regular task (> tomorrow)
                $readableDate = $taskDate->format(env('APP_LOCALE_OTHERS_MASK','l,j \de F'));
                $fields = $regularTasks->get($task->get('date'));

                if (is_null($fields)){

                    //First task with this date, init the collection
                    $fields = collect();
                    $fields->put("readableDate",$readableDate);
                    $fields->put("tasks",collect());  
                }

                $tasks = $fields->get('tasks');
                $tasks->push($title);
                $fields->put("tasks",$tasks);
                $regularTasks->put($task->get('date'),$fields);
            }
        }

        $regularTasks = $regularTasks->sortKeys();

        // log::debug($overdueTasks);
        // log::debug($todayTasks);
        // log::debug($tomorrowTasks);
        // log::debug($regularTasks);

        return view('index',['date' => $date,'overdueTasks' => $overdueTasks, 'todayTasks' => $todayTasks, 'tomorrowTasks' => $tomorrowTasks,'regularTasks' => $regularTasks, 'refreshRate' => $refreshRate]);
    }
}
