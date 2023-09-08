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