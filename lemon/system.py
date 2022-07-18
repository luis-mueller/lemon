import io
import time
from lemon.ctx import AsyncNodeContext, NodeContext
from lemon.utils import Severity, bold_str, severity_to_message
import os
import psutil
import subprocess
import pathlib


class NodePIDNotFound(Exception):
    pass


class LogFileService:
    def open(ctx: "NodeContext", mode: "str") -> "io.TextIOWrctxer":
        logdir = str(pathlib.Path.home()) + '/lemon/logs'

        if not os.path.exists(logdir):
            os.makedirs(logdir)

        return open(f'{logdir}/{ctx.name}.txt', mode)


class ProcessService:
    async def self_register(ctx: "AsyncNodeContext"):
        await ctx.redis_client.set(f"{ctx.mesh}:{ctx.name}:pid", os.getpid())

    def self_terminate():
        psutil.Process().terminate()

    def start(ctx: "NodeContext",
              additional_args: "list[str]") -> "subprocess.Popen":

        logfile = LogFileService.open(ctx, 'wb')
        return subprocess.Popen([
            ctx.node,
            ctx.mesh,
            '-n', ctx.name
        ] + additional_args, stdout=logfile, stderr=logfile)

    def stop(ctx: "NodeContext"):
        pid = ProcessService.get_pid(ctx)
        process = psutil.Process(pid)
        process.send_signal(2)
        time.sleep(1)

        ProcessService.force_quit(process)

    def is_running(ctx: "NodeContext"):
        try:
            pid = ProcessService.get_pid(ctx)
            return psutil.pid_exists(pid)
        except NodePIDNotFound:
            return False

    def get_pid(ctx: "NodeContext") -> int:
        pid = ctx.redis_client.get(f"{ctx.mesh}:{ctx.name}:pid")

        if not pid:
            raise NodePIDNotFound

        return int(pid.decode('utf-8'))

    def force_quit(process: "psutil.Process"):
        if process.is_running():
            severity_to_message(Severity.Information, (
                f'Process {bold_str(process.pid)}'
                + ' has to be interrupted forcefully'
            ))
            process.terminate()
