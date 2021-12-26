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

class Controller extends BaseController
{
    use AuthorizesRequests, DispatchesJobs, ValidatesRequests;

    public function index()
    {

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

            if (env('ADD_HOUR',True) & isset($task['due']['datetime'])){
                
                //Log::debug($task);

                $dateTest = new Date($task['due']['datetime']);
                $dateTest->setTimezone(env('APP_TIMEZONE','Europe/Madrid'));
    
                if ($dateTest->hour < 10){
                    $hourString = '0' . strval($dateTest->hour);
                }else{
                    $hourString = strval($dateTest->hour);
                }

                if ($dateTest->minute < 10){
                    $minuteString = '0' . strval($dateTest->minute);
                }else{
                    $minuteString = strval($dateTest->minute);
                }

                $content = '[' . $hourString . ':' . $minuteString . '] ' . $content;

                //Log::debug($dateTest->hour);
                //Log::debug($dateTest->minute);

            }

            // If task longer than TASK_MAX_LENGHT, truncate it so it fits in Kindle Touch width
            $content = Str::of($content)->limit(env('TASK_MAX_LENGHT',66));

            // Add the processed task to $filteredtasks
            $taskAsCollection = collect();
            $taskAsCollection->put('date',$task['due']['date']);
            $taskAsCollection->put('title',$content);
            $filteredtasks->push($taskAsCollection);
        }

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

        $today = new Date('today');

        foreach($filteredtasks as $task){

            $taskDate = new Date($task->get('date'));

            if ($today->diffInHours($taskDate,false) < 0){
                // Overdue Task

                $tasks = $overdueTasks->get('tasks');
                $tasks->push($task->get('title'));
                $overdueTasks->put('tasks',$tasks);

            }else if ($taskDate->equalTo($today)){
                // Today Task

                $tasks = $todayTasks->get('tasks');
                $tasks->push($task->get('title'));
                $todayTasks->put('tasks',$tasks);

            }else if ($taskDate->diffInDays($today) == 1){
                // Tomorrow Task

                $tasks = $tomorrowTasks->get('tasks');
                $tasks->push($task->get('title'));
                $tomorrowTasks->put('tasks',$tasks);


            }else{
                // Regular task (> tomorrow)
                // Readable format 'martes, 14 de diciembre'
                $readableDate = $taskDate->format(env('APP_LOCALE_OTHERS_MASK','l,j \de F'));

                $fields = $regularTasks->get($task->get('date'));

                if (is_null($fields)){
                    $fields = collect();
                    $fields->put("readableDate",$readableDate);
                    $fields->put("tasks",collect());  
                }
                $tasks = $fields->get('tasks');
                $tasks->push($task->get('title'));
                $fields->put("tasks",$tasks);
                $regularTasks->put($task->get('date'),$fields);
            }
        }

        $regularTasks = $regularTasks->sortKeys();

        log::debug($overdueTasks);
        log::debug($todayTasks);
        log::debug($tomorrowTasks);
        log::debug($regularTasks);

        return view('index',['date' => $date,'overdueTasks' => $overdueTasks, 'todayTasks' => $todayTasks, 'tomorrowTasks' => $tomorrowTasks,'regularTasks' => $regularTasks, 'refreshRate' => $refreshRate]);
    }
}
