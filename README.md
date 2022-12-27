# FastSSH 0.0.1

Módulo criado com o objetivo de facilitar a conexão com servidores via SSH, permitindo envio de comandos Bash e Arquivos

### Python (com [PIP](https://www.treinaweb.com.br/blog/gerenciando-pacotes-em-projetos-python-com-o-pip))
```py
python ^= 3.10
```
Caso queira instalar o python utilizando [**Anaconda**](https://www.anaconda.com/)
```py
conda create -n fast_ssh python=3.10
conda activate fast_ssh
```

### Dependências
No diretório clonado, envie o seguinte comando
```
python -m pip install -r requirements.txt
```

---

### Como utilizar

Após ajustar o main.py, execute o seguinte comando:
```python
python main.py
```

Seguindo o exemplo do arquivo main.py

```py
import sys
from fast_ssh import SSH, SSHExecuteResult


# 0. Informações de Conexão (exemplo)
host: str = "192.333.12.444"
username: str = "pi"
password: str = "raspberry"

# 1. Validando Conexão
if not SSH.is_valid_connection(host, username, password):
    sys.exit("Conexão inválida")

# 2. Instanciando via with para 'close' automático após o uso
with SSH(host, username, password) as ssh:
    
    # 2.1. Método exec permite enviar os comandos que serão executados na máquina
    # Exemplo deletando um arquivo via RM
    ex: SSHExecuteResult = ssh.exec(
        r"rm /home/developer/ArquivoParaDeletar.txt -f")
    
    # 2.2. O exec retorna um Objeto SSHExecuteResult com as informações da Execução
    stdout: str = ex.get_stdout()
    stderr: str = ex.get_stderr()
    
    if ex.is_fail():
        print(stdout)
        print(f"Falha durante a execução: {stderr}")
    else:
        print(stdout)

    # 2.3. Caso esta execução aguarde uma resposta é possível enviar via Flush
    ex.flush("yes")

    # 2.4. Caso a execução no servidor seja de um script que demore
    #      para executar, pode ser utilizada uma execução assíncrona
    #      que envia as informações aos poucos via callback
    #      (não possui retorno)
    ssh.async_exec(
        r"python3 /home/developer/script_demorado.py",
        lambda stdout: print(stdout.decode(), end="")
    )

    # Se fosse utilizada a versão normal, ele iria printar todos os resultados
    # de uma vez, após acabar tudo
    ex2: SSHExecuteResult = ssh.exec(
        r"python3 /home/developer/script_demorado.py")

    # 2.5. Enviando/criando arquivos via FTP 
    #      (caso já exista o arquivo, ele terá o conteúdo trocado)
    try:
        ssh.send_file(
            filename=r'/home/developer/NovoArquivo.txt', 
            content='Conteúdo em bytes para o arquivo'.encode()
        )
    except Exception as e:
        print(f"Falha ao criar arquivo: {e}")

    # Caso queira enviar um arquivo com base em um arquivo local
    # Basta enviar o caminho do arquivo no "content" em vez do conteúdo em bytes
    try:
        ssh.send_file(
            filename=r'/home/developer/NovoArquivo.txt', 
            content=r'C:/Documentos/NovoArquivo.txt'
        )
    except Exception as e:
        print(f"Falha ao enviar arquivo: {e}")

    # 2.6. Baixando arquivos remotos via FTP
    try:
        conteudo: bytes = ssh.download_file(
            filename=r'/home/developer/NovoArquivo.txt')

        # O conteúdo do arquivo é retornado em bytes
        # Permitindo que seja utilizado livremente

        # Salvando localmente arquivo baixado 
        with open(r'C:/Documentos/NovoArquivoBaixado.txt', 'wb') as arquivo:
            arquivo.write(conteudo)
        
    except Exception as e:
        print(f"Falha ao baixar arquivo: {e}")
```
