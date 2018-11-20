import subprocess
import click
import threading
import logging
import requests
from time import sleep


class Monitor:
    def __init__(self, url, max_memory_size, request_timeout, program_name):
        self.url = url
        self.request_timeout = request_timeout
        self.program_name = program_name
        self.max_memory_size = max_memory_size
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
                pid = subprocess.run(
                    ['supervisorctl', 'pid', self.program_name],
                    capture_output=True).stdout
                if not pid:
                    raise Exception('Error getting pid of "{}" program'.format(self.program_name))

                status = subprocess.run(
                    self.pscommand % pid,
                    shell=True,
                    capture_output=True).stdout
                if not status:
                    raise Exception('Error getting status of "{}" program (pid - {})'.format(
                        self.program_name,
                        pid))
                if int(status) / 1024 > int(self.max_memory_size):
                    self.restart_program()

            except Exception as e:
                self.logger.error(e)

            sleep(self.request_timeout)

    def run_checker(self):
        while 1:
            try:
                r = requests.get(self.url)
                assert r.status_code < 500
            except Exception:
                self.restart_program()

            sleep(self.request_timeout)

    def restart_program(self):
        try:
            status = subprocess.run(
                ['supervisorctl', 'restart', self.program_name],
                capture_output=True)
            if status.returncode == 0:
                self.logger.info('Restarted {}\n'.format(self.program_name))
            else:
                raise Exception('Restart error: {}'.format(status.stderr))
        except Exception as e:
            self.logger.error(e)


@click.command()
@click.option('--program-name', '-p', help='Program name (supervisor)', required=True)
@click.option('--url', help='Request url', required=False)
@click.option('--max-memory-size', '-m', help='Set max memory size of process (Mb)', required=False)
@click.option('--request-timeout', '-t', default=60, help='Request timeout (s)')
def main(program_name, url, max_memory_size, request_timeout):
    monitor = Monitor(
        url=url,
        max_memory_size=max_memory_size,
        program_name=program_name,
        request_timeout=request_timeout
    )

    if max_memory_size and url:
        threading.Thread(target=monitor.run_monitor).start()
        threading.Thread(target=monitor.run_checker).start()
    elif max_memory_size:
        monitor.run_monitor()
    else:
        monitor.run_checker()


if __name__ == '__main__':
    main()
