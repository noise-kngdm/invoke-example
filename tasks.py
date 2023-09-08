"""
Invoke tasks.

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
"""

import time
import git
import shutil
import os

from datetime import datetime
from pathlib import Path
from invoke import task, Responder
from invoke.exceptions import Failure

DJANGO_EXEC = 'docker compose exec django'


@task
def down(ctx):
    """Stop all the services"""
    ctx.run('docker compose down -t0 -v --remove-orphans')


@task(help={'all': 'Use the default docker file instead of the dev one'})
def up(ctx, all=False):
    """Create and start the containers"""
    if all:
        ctx.run('docker compose up -d')
    else:
        ctx.run(f'docker compose -f {ctx.DEV_DOCKER_COMPOSE} up -d')


@task(help={'command': 'Command that should be runned by Django',
            'watchers': 'Custom watchers that should be used by invoke'})
def command(ctx, command='', watchers=None):
    """Run a django command"""
    if watchers is None:
        watchers = []
    ctx.run(f"{DJANGO_EXEC} python manage.py {command}", pty=True, watchers=watchers)


def unapplied_migrations(ctx) -> bool:
    """
    Check if there are unapplied migrations.

    Returns:
        bool: True if there are unapplied migrations, False otherwise.
    """
    try:
        eso = ctx.run(f"{DJANGO_EXEC} bash -c 'python manage.py showmigrations'", hide='both')
        if '[ ]' in eso.stdout:
            return True
    except Exception as e:
        print(f"Error showing unapplied migrations: {e}")
        pass
    return False


@task
def checkmigrations(ctx):
    """Check if there are migrations to be applied"""
    if unapplied_migrations(ctx):
        print('There are unapplied migrations')
    else:
        print('All migrations have been applied')


@task
def db(ctx, skip_db_wipe=False):
    """Reset and fill the db with sample data"""
    while unapplied_migrations(ctx):
        print("There are unapplied migrations, sleeping...")
        time.sleep(ctx.SECONDS_SLEEP)

    responder_y_n = Responder(
        pattern='This command will seed new data\(and optionally wipe the database\)\. Continue\? \(Y/N\)',
        response='y\n'
    )

    parsed_args = ""
    if skip_db_wipe:
        parsed_args += ' --skip_db_wipe'

    while True:
        try:
            command(ctx, command=f'refresh_db {parsed_args}', watchers=[responder_y_n])
        except KeyboardInterrupt:
            return
        except Failure:
            time.sleep(1)
            continue
        break


@task(help={'follow': 'If the command should continue streaming the new output from the container\'s STDOUT and STDERR',
            'service': 'Service whose logs should be printed. Defaults to django.'})
def logs(ctx, follow=False, service='django'):
    """Print the logs of a service"""
    ctx.run(f"docker compose logs {'--follow' if follow else ''} {service}", pty=True)


@task(help={'no_cache': 'If the cache should be ignored when building the images'})
def build(ctx, no_cache=False):
    """Build all the services"""
    docker_args = ' '.join(['--' + flag for flag in ctx.DOCKER.BUILD_ARGS])
    if no_cache:
        docker_args += ' --no-cache'
    ctx.run(f"docker compose -f {ctx.DEV_DOCKER_COMPOSE} build {docker_args}", pty=True)


def tests_roots(tests):
    roots = []
    for test in tests.split(','):
        working_tests = test.replace('.', '/')
        roots.append(working_tests.split('/')[0])
    return roots


def selected_tests(tests):
    selected_tests = []
    for test in tests.split(','):
        if '/' in test:
            test = test.replace('/', '.')
        if test.endswith('.py'):
            test = test[: -3]
        test = test.rstrip('.')

        selected_tests.append(test)
    return selected_tests


@task(help={
    'test': 'Test that should be run. Specified with . or / as path delimiter. Select different tests with a comma. e.g. "inv test -t \'reports.tests.test_views,reports.tests.test_models\'"',
    'keywords': 'Keywords that should be used to filter the tests.',
    'coverage': 'If the coverage report should be displayed.'
})
def test(ctx, test, keywords='', coverage=False):
    """Run a unit test"""
    roots = tests_roots(test)
    tests = selected_tests(test)
    test_flags = ' '.join(['--' + flag for flag in ctx.TEST.FLAGS])

    command_keywords = '' if not keywords else f'-k {keywords}'

    executer = f"coverage run --source='{','.join(roots)}'" if coverage else 'python'

    command = f"{DJANGO_EXEC} {executer} manage.py test {test_flags} {' '.join(tests)} {command_keywords}"

    ctx.run(command, pty=True)
    if coverage:
        ctx.run(f"{DJANGO_EXEC} coverage combine; {DJANGO_EXEC} coverage report --include='{'*,'.join(roots)}*'", pty=True)


@task(help={
    'merge': 'If the migrations should be merged into one file',
})
def makemigrations(ctx, merge=False, empty=False):
    """Call the django makemigrations command"""

    if merge:
        command(ctx, 'makemigrations --merge')
    else:
        command(ctx, 'makemigrations')


@task
def showmigrations(ctx):
    """Call the django makemigrations command"""
    command(ctx, 'showmigrations')


@task
def sqlmigrate(ctx, migration):
    """
    Call the django sqlmigrate command to show
    the SQL code that will correspond to a given migration.
    """
    command(ctx, f'sqlmigrate {migration}')


@task(help={'migration': 'Which migration should be applied/unapplied. e.g. "inv migrate -m \'reports 00145\'"'})
def migrate(ctx, migration=""):
    """Call the django migrate command"""
    command(ctx, f'migrate {migration}')


@task
def bash(ctx, service='django', rest='', hide=False):
    """Invoke bash in the specified service. Django by default"""
    command = f'-c "{rest}"' if rest else ''
    ctx.run(f"docker compose exec {service} bash {command}", pty=True, hide=hide)


def copy_file(file, destination):
    """Copy a file to a destination"""
    try:
        shutil.copy(file, Path(destination) / Path(file).name)
    except FileExistsError:
        print(f'File {file} already exists in {destination}. Overwriting...')
        Path(destination).joinpath(Path(file).name).unlink()
        copy_file(file, destination)


def copy_folder(folder, destination):
    """Copy a folder to a destination"""
    try:
        shutil.copytree(folder, Path(destination) / Path(folder).name)
    except FileExistsError:
        print(f'Folder {folder} already exists in {destination}. Overwriting...')
        shutil.rmtree(Path(destination) / Path(folder).name)
        copy_folder(folder, destination)


def check_project_ownership(path):
    """
    Recursively check if all files in the project are owned by the user running the script,
    raise an exception otherwise.
    """
    if path.is_dir():
        for child in path.iterdir():
            check_project_ownership(child)
    else:
        if Path(path).stat().st_uid != os.getuid():
            raise Exception


@task
def clean(ctx):
    """
    Cleans and rebuild the whole environment to make it lighter.
    Backups the files and folders specified in the CLEAN_ENV.BK_FILES and CLEAN_ENV.BK_FOLDERS
    variables (see the invoke.yaml file).
    """
    project_root = Path(__file__).parent.resolve()

    try:
        check_project_ownership(project_root)
    except Exception:
        print(f'There are files that aren\'t owned by the user running the script, run `sudo chown -R $USER:$USER {project_root}` and try again.')
        return

    BACK_DATE_FORMAT = r'%m-%d-%yT%H%M%S'
    backup_dir = ctx.CLEAN_ENV.BAK_DIR if ctx.CLEAN_ENV.BAK_DIR[-1] == '/' else ctx.CLEAN_ENV.BAK_DIR + '/'
    folder_name = datetime.now().strftime(BACK_DATE_FORMAT)
    backup_folder_name = f"{backup_dir}{folder_name}/"
    Path(backup_folder_name).mkdir(parents=True, exist_ok=True)

    print(f'Backing up to {backup_folder_name}...')
    for file in ctx.CLEAN_ENV.BK_FILES:
        copy_file(file, backup_folder_name)
    for folder in ctx.CLEAN_ENV.BK_FOLDERS:
        copy_folder(folder, backup_folder_name)

    print('Cleaning...')
    repo = git.Repo(project_root)
    repo.git.clean('-fdx')

    print('Restoring backups...')
    for file in ctx.CLEAN_ENV.BK_FILES:
        copy_file(backup_folder_name + file, project_root)
    for folder in ctx.CLEAN_ENV.BK_FOLDERS:
        copy_folder(backup_folder_name + folder, project_root)

    if ctx.CLEAN_ENV.REMOVE_BACKUP_AFTER_COPY:
        print('Removing backups...')
        shutil.rmtree(backup_folder_name)
    print('Done!')


@task(help={'all': 'Use the default docker file instead of the dev one'}, pre=[down], post=[db])
def reset(ctx, all=False):
    """Relaunch the docker environment and fill the db with sample data"""
    up(ctx, all)


@task
def shell(ctx):
    """Invoke django shell."""
    command(ctx, 'shell')


@task(help={'script': 'Script that should be runned by Django. Path relative to the django project folder.'})
def script(ctx, script):
    """Invoke a django script."""
    bash(ctx, rest=f"python manage.py shell < {script}")


@task
def docker_prune(ctx):
    """Run the docker system prune command to free up disk space"""
    ctx.run('docker system prune -af')
