#

Invoke sample tasks

To install run:

```
pip3 install invoke GitPython
```

To list all tasks run:

```
inv --list
```

To run a task run:

```
inv <task_name>
```

To run a task with a parameter run:

```
inv <task_name> --<parameter_name> <parameter_value>
```

The "<parameter_value>" part is optional if the parameter is a boolean.
Multiple parameters can be specified.

To get help for a task run:

```
inv --help <task_name>
```

## List of current tasks

Extracted running `inv --list`.

```
Available tasks:

  bash              Invoke bash in the specified service. Django by default
  build             Build all the services
  checkmigrations   Check if there are migrations to be applied
  clean             Cleans and rebuild the whole environment to make it light and PHI-free.
  command           Run a django command
  cypress           Open the Cypress GUI
  db                Reset and fill the db with sample data
  docker-prune      Run the docker system prune command to remove all unused images, containers, networks and volumes
  down              Stop all the services
  logs              Print the logs of a service
  makemigrations    Call the django makemigrations command
  merge             Call the merge_patients command
  migrate           Call the django migrate command
  reset             Relaunch the docker environment and fill the db with sample data
  restart           Restart a service. All services by default.
  script            Invoke a django script.
  setup-cypress     Check if Cypress is configured and install if necessary.
  shell             Invoke django shell.
  showmigrations    Call the django makemigrations command
  sqlmigrate        Call the django sqlmigrate command to show
  test              Run a unit test
  up                Create and start the containers
```
