import subprocess
import click
import threading
import logging
from time import sleep
from requests import get


class Monitor:
    def __init__(self, url, request_timeout, program_name):
        self.url = url
        self.request_timeout = request_timeout
        self.program_name = program_name
        self.pscommand = 'ps -q %s -o "size" --no-header'
        self.logger = logging.getLogger('supervisor-monitor')

        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        stderr = logging.FileHandler('stderr.log')
        stderr.setLevel(logging.ERROR)
        stderr.setFormatter(log_formatter)

        stdout = logging.FileHandler('stdout.log')
        stdout.setLevel(logging.INFO)
        stdout.setFormatter(log_formatter)

        self.logger.addHandler(stderr)
        self.logger.addHandler(stdout)

    def run_monitor(self):
        while 1:
            try:
                pid = subprocess.run(['supervisorctl', 'pid', self.program_name]).STDOUT
                if not pid:
                    raise Exception('Error: pid not found!')

                status = subprocess.run(self.pscommand % pid, shell=True).STDOUT
                if not status:
                    raise Exception('Error: error getting status')
                self.logger.info(status)
            except Exception as e:
                self.logger.error(e)

            sleep(self.request_timeout)

    def run_checker(self):
        while 1:
            try:
                get(self.url)
            except Exception:
                self.restart_program()

            sleep(self.request_timeout)

    def restart_program(self):
        try:
            status = subprocess.run(['supervisorctl', 'restart', self.program_name])
            if status.returncode == 0:
                self.logger.info('Restarted {}\n'.format(self.program_name))
            else:
                raise Exception('Restart error')
        except Exception as e:
            self.logger.error('Restart error: {}\n'.format(e))


@click.command()
@click.option('--url', help='Request url', required=True)
@click.option('--program-name', '-p', help='Program name (supervisor)', required=True)
@click.option('--request-timeout', '-t', default=60, help='Request timeout (s)')
def main(url, program_name, request_timeout):
    monitor = Monitor(
        url=url,
        program_name=program_name,
        request_timeout=request_timeout
    )

    threading.Thread(target=monitor.run_checker).start()
    threading.Thread(target=monitor.run_monitor).start()


if __name__ == '__main__':
    main()
