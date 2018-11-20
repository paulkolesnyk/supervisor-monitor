import subprocess
import click
import logging
import requests
from time import sleep


class Monitor:
    def __init__(self, program_name, timeout=60, request_url=None, request_timeout=None,
                 memory_max_size=None):
        self.program_name = program_name
        self.timeout = timeout
        if not request_url and not memory_max_size:
            raise ValueError('request_url or memory_max_size required')
        self.request_url = request_url
        self.request_timeout = request_timeout
        self.memory_max_size = int(memory_max_size)
        self.pscommand = 'ps -q %s -o "size" --no-header'
        self.logger = logging.getLogger('supervisor-monitor')

    def check_memory(self):
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
            raise Exception('Error getting status of "{}" program (pid - {})'
                            .format(self.program_name, pid))

        memory_size = int(status) / 1024
        if memory_size > self.memory_max_size:
            return RuntimeError('Memory limit exceeded: {}M > {}M'
                                .format(memory_size, self.memory_max_size))

    def check_request(self):
        try:
            r = requests.get(self.request_url, timeout=self.request_timeout)
            if 500 <= r.status_code < 600:
                msg = u'%s Server Error: %s for url: %s' % (r.status_code, r.reason, r.url)
                return requests.HTTPError(msg, response=r)
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
            self.logger.debug('Sleeping %s', self.timeout)
            sleep(self.timeout)

    def restart(self):
        status = subprocess.run(
            ['supervisorctl', 'restart', self.program_name],
            capture_output=True)
        if status.returncode == 0:
            self.logger.info('Restarted {}\n'.format(self.program_name))
        else:
            raise Exception('Restart error: {}'.format(status.stderr))


@click.command()
@click.option('--program-name', '-p', help='Program name (supervisor)', required=True)
@click.option('--timeout', help='Monitor timeout', default=60, required=False)
@click.option('--request-url', help='Request url', required=False)
@click.option('--request-timeout', '-t', default=5, help='Request timeout (s)')
@click.option('--memory-max-size', '-m', help='Set max memory size of process (Mb)', required=False)
def main(**kwargs):
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
    Monitor(**kwargs)()


if __name__ == '__main__':
    main()
