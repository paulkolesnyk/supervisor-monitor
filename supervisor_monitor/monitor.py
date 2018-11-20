import subprocess
import logging
from time import sleep

import click
import requests


class Monitor:
    def __init__(self, program_name, sleep=60, request_url=None, request_timeout=None,
                 memory_max_size=None):
        self.program_name = program_name
        self.sleep = sleep
        if not request_url and not memory_max_size:
            raise ValueError('request_url or memory_max_size required')
        self.request_url = request_url
        self.request_timeout = request_timeout
        self.memory_max_size = int(memory_max_size)
        self.pscommand = 'ps -q %s -o "size" --no-header'
        self.logger = logging.getLogger('supervisor-monitor')

    def check_memory(self):
        pid = int(subprocess.run(
            'supervisorctl pid {}'.format(self.program_name),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True).stdout)
        if not pid:
            raise Exception('Error getting pid of "{}" program'.format(self.program_name))

        stdout = subprocess.run(
            self.pscommand % pid,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True).stdout
        if not stdout:
            raise Exception('Error getting status of "{}" program (pid - {})'
                            .format(self.program_name, pid))

        memory_size = int(stdout) / 1024
        if memory_size > self.memory_max_size:
            return RuntimeError('Memory limit exceeded: {}M > {}M'
                                .format(memory_size, self.memory_max_size))
        self.logger.debug('Memory %s <= %s', memory_size, self.memory_max_size)

    def check_request(self):
        try:
            r = requests.get(self.request_url, timeout=self.request_timeout)
            if 500 <= r.status_code < 600:
                msg = u'%s Server Error: %s for url: %s' % (r.status_code, r.reason, r.url)
                return requests.HTTPError(msg, response=r)
            self.logger.debug('Request %s', r)
        except requests.RequestException as exc:
            return exc

    def __call__(self):
        while True:
            exc = None
            if not exc and self.memory_max_size:
                exc = self.check_memory()
            if not exc and self.request_url:
                exc = self.check_request()
            if exc:
                self.logger.error('Restarting: reason %s', exc)
                self.restart()
            self.logger.debug('Sleeping %s', self.sleep)
            sleep(self.sleep)

    def restart(self):
        status = subprocess.run(
            'supervisorctl restart {}'.format(self.program_name),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        if status.returncode == 0:
            self.logger.info('Restarted {}\n'.format(self.program_name))
        else:
            raise Exception('Restart error: {}'.format(status.stderr))


@click.command()
@click.option('--program-name', '-p', help='Program name (supervisor)', required=True)
@click.option('--sleep', help='Monitor sleep', default=60, required=False)
@click.option('--log-level', '-l', help='Log level', default='DEBUG', required=False)
@click.option('--request-url', '-u', help='Request url', required=False)
@click.option('--request-timeout', '-t', default=5, help='Request timeout (s)')
@click.option('--memory-max-size', '-m', help='Set max memory size of process (Mb)', required=False)
def main(program_name, log_level, **kwargs):
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                        level=logging.getLevelName(log_level.upper()))
    Monitor(program_name, **kwargs)()


if __name__ == '__main__':
    main()
