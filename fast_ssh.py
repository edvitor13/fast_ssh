from __future__ import annotations
from io import BytesIO, TextIOWrapper
from typing import Callable
import hashlib
import re

from paramiko import PasswordRequiredException, RSAKey, SSHClient, AutoAddPolicy
from paramiko.channel import ChannelStdinFile, ChannelFile, ChannelStderrFile


__all__ = [
    'SSHPasswordRequiredException',
    'SSHExecuteResult',
    'SSH'
]


class SSHPasswordRequiredException(Exception):
    pass


class SSHExecuteResult:

    def __init__(
        self, 
        ssh: SSH,
        stdin: ChannelStdinFile | None = None, 
        stdout: ChannelFile | None = None, 
        stderr: ChannelStderrFile | None = None,
        exit_code: int | None = None,
        *,
        server_fail: bool = False
    ) -> None:
        self.ssh = ssh
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.__is_server_fail = server_fail
    
    
    def is_fail(self) -> bool:
        if self.is_server_fail():
            return True
        
        if self.exit_code != 0:
            return True
        
        return False


    def is_server_fail(self) -> bool:
        return self.__is_server_fail


    def get_exit_code(self) -> int | None:
        return self.exit_code


    def get_stdout(
        self, 
        *, 
        _bytes: bool = False, 
        lines: bool = False
    ) -> str | bytes | list[str]:

        if self.stdout is None:
            return b'' if _bytes else ''
        
        if _bytes:
            return self.stdout.read()

        if lines:
            return self.stdout.readlines()
        
        return self.stdout.read().decode()


    def get_stderr(
        self, 
        *, 
        _bytes: bool = False, 
        lines: bool = False
    ) -> str | bytes | list[str]:

        if self.stderr is None:
            return b'' if _bytes else ''
        
        if _bytes:
            return self.stderr.read()
        
        if lines:
            return self.stderr.readlines()
        
        return self.stderr.read().decode()


    def flush(self, data: str | bytes) -> None:
        if self.stdin is None:
            return None

        self.stdin.write(data)
        self.stdin.flush()
        return None



class SSH:

    last: SSH

    def __init__(
        self, 
        host: str, 
        username: str, 
        password: str | None = None, 
        pem: str | None = None
    ) -> None:
        self.client: SSHClient
        self._connect_client(host, username, password, pem)
        SSH.last = self

    
    def _connect_client(
        self, 
        host: str, 
        username: str, 
        password: str | None, 
        pem: str | None
    ) -> None:
        if pem is not None:
            self.__connect_client_by_pen(
                host, username, pem, password)
            return None

        self.__connect_client_by_password(
            host, username, password)
    

    def __connect_client_by_pen(
        self, 
        host: str, 
        username: str, 
        pem: str,
        password: str | None
    ):
        _pem = None

        try:
            _pem = RSAKey.from_private_key_file(pem, password)

        except PasswordRequiredException as e:
            raise SSHPasswordRequiredException(
                "PEM file is encrypted and requires a valid password")

        except Exception:
            try:
                _pem = RSAKey.from_private_key(
                    TextIOWrapper(BytesIO(pem.strip().encode())), 
                    password
                )

            except PasswordRequiredException as e:
                raise SSHPasswordRequiredException(
                    "PEM is encrypted and requires a valid password")

            except Exception as e:
                raise e

        try:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())

            client.connect(
                hostname=host, 
                username=username, 
                pkey=_pem)

            self.client = client
        except Exception as e:
            raise e
    

    def __connect_client_by_password(
        self, 
        host: str, 
        username: str, 
        password: str | None
    ):
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            client.connect(
                hostname=host, 
                username=username, 
                password=password)

            self.client = client
        except Exception as e:
            raise e


    def __enter__(self) -> SSH:
        return self


    def __exit__(self, *args):
        self.close()


    def exec(
        self,
        command: str | list[str],
        bufsize: int = -1,
        timeout: float | None = None,
        get_pty: bool = False,
        environment: dict[str, str] | None = None
    ) -> SSHExecuteResult:
        try:
            if type(command) is list:
                _command = ";".join(command)
            else:
                _command = str(command)
                
            _stdin, _stdout, _stderr = self.client.exec_command(
                _command, bufsize, timeout, get_pty, environment)
        except:
            return SSHExecuteResult(self, server_fail=True)

        exit_code = _stdout.channel.recv_exit_status()

        return SSHExecuteResult(self, _stdin, _stdout, _stderr, exit_code)

    
    def async_exec(
        self,
        command: str | list[str],
        callback: Callable[[bytes], None]
    ) -> None:
        if type(command) is list:
            _command = ";".join(command)
        else:
            _command = str(command)
                
        _stdin, _stdout, _stderr = self.client.exec_command(
            _command, get_pty=True)

        while True:
            v = _stdout.channel.recv(1024)
            if not v:
                break

            callback(v)
        
        if _stdout.channel.recv_exit_status() != 0:
            raise Exception("Execution resulted in failure")


    def close(self):
        self.client.close()


    def download_file(self, filename: str) -> bytes:
        with self.client.open_sftp() as ftp:
            with ftp.open(filename, "rb") as file:
                return file.read()


    def send_file(self, filename: str, content: bytes | str):
        with self.client.open_sftp() as ftp:
            with ftp.open(filename, "wb") as file:
                try:
                    with open(content, "rb") as local_file:
                        file.write(local_file.read())
                except:
                    file.write(content)


    def validate_files_hash(self, remote_filename: str, local_filename: str):
        with self.client.open_sftp() as ftp:
            
            with ftp.open(remote_filename, "rb") as remote_file:
                remote_md5 = hashlib.md5(remote_file.read()).hexdigest()
            
            with open(local_filename, "rb") as local_file:
                local_md5 = hashlib.md5(local_file.read()).hexdigest()

            if remote_md5 != local_md5:
                raise ValueError(
                    f"Remote file hash <{remote_md5}> is diff "
                    f"of local file hash <{local_md5}>")


    def edit_file(self, filename: str, callback: Callable[[bytes], bytes]):
        file: bytes = self.download_file(filename)
        edited_file = callback(file)
        self.send_file(filename, edited_file)

    
    def edit_file_regex_replace(
        self, 
        filename: str, 
        pattern: str, 
        replacer: str, 
        count: int = 0, 
        flags: int = 0
    ):
        return self.edit_file(
            filename, 
            lambda file: re.sub(pattern, replacer,
                file.decode(), count=count, flags=flags).encode()
        )

    
    def edit_file_replace(
        self, 
        filename: str, 
        old: str, 
        new: str, 
        count: int = -1
    ):
        return self.edit_file(
            filename, 
            lambda file: file.decode().replace(old, new, count=count)
        )


    @staticmethod
    def is_valid_connection(
        host: str, 
        username: str, 
        password: str | None = None, 
        pem: str | None = None
    ):
        try:
            SSH(host, username, password, pem).close()
            return True
        except Exception as e:
            return False
