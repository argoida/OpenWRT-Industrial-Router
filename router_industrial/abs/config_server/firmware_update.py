import sys, os
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor')
import datetime
import json
import debug
import abs_utils
import abs_serial_number
from config_manager import config_manager
from http_util_class import http_util
import program_release_version
from cript_lib import abs_cript

logger = debug.get_logger()


file_download = '/tmp/new_firmware.pac'
file_packet = '/tmp/new_firmware.tar.gz'
file_metadata = '/tmp/new_firmware.http'
file_stderr = '/tmp/new_firmware.stderr'
file_on_process = '/tmp/new_firmware.on_process'


def do_download(parms):
    cfm = config_manager('abs_conversor')
    if not cfm.read_config():
        return "Problema tentando ler as configuracoes para fazer o update"

    returnmsg = "Falha na configuracao do update."
    isok = False

    with open(file_on_process, 'w+') as fpproc:
        now = datetime.datetime.now()
        fpproc.write(str(now) + ' Iniciando o download do pacote de update do firmware \n')

        try:
            ## ATENCAO ALEX 2019 02 07   a configuracao do firmware update sera hardcoded porque nao eh mais necessario ser configuravel
            ##  O comando para iniciar o download do pacote ja permite passar todos os parametros para substituirem os defaults.
            conv_cfg = {
                'url' : 'http://www.yourupdatesite.com:80/Web/otap/#part#/#version#?sn=#serial#',
                'timeout': '60'
            }
            logger.debug(str(conv_cfg))

            ## Da preferencia para os parametros que vieram junto com o comando. Se nao, usa o que estiver na configuracao
            staux = 'url'
            url = conv_cfg[staux]
            if staux in parms :
                url = parms[staux]

            staux = 'timeout'
            sttimeout = conv_cfg[staux]
            if staux in parms :
                sttimeout = parms[staux]

            try:
                timeout = int(sttimeout)
            except Exception as inst:
                timeout = 90

            strret = url
            streplace = '#part#'
            partnumber = abs_serial_number.get_abs_part_number()
            while strret.find(streplace) > -1:
                strret = strret.replace(streplace, partnumber)

            streplace = '#serial#'
            serialnumber = abs_serial_number.get_abs_serial_number()
            while strret.find(streplace) > -1:
                strret = strret.replace(streplace, serialnumber)

            streplace = '#version#'
            version = program_release_version.release_version
            while strret.find(streplace) > -1:
                strret = strret.replace(streplace, version)

            url = strret

            # remover os arquivos para garantir nao ter ficado lixo
            try:
                os.remove( file_metadata)
                os.remove( file_download)
            except Exception as e :
                pass    ## nao imnporta se os arquivos nao existam

            part = abs_utils.separa_uri(url)
            if part['port'] == '':
                part['port'] = None

            httpaux = http_util(part['protocol'], part['hostname'], part['port'], timeout)
            uri = abs_utils.monta_uri(None, None, None, part['path'], part['query_string'])
            head = httpaux.get( uri, content_to=file_download)

            if not head or not 'status' in head :
                logger.error('Nao conseguiu ler o pacote com o update')
                returnmsg = "Nao terminou de baixar, ou falhou sem resposta para o GET " + url
                head = {}
                head['status'] = -1 # indica que deu problema
            else:
                logger.debug('Retorno do post para pegar a configuracao ' + str(head['status']))
                if head['status'] >= 200 and head['status'] < 300:
                    returnmsg = 'Pacote lido'
                    isok = True
                else:
                    returnmsg = "Falha ao tentar baixar o pacote do update - server respondeu " + str(head['status']) + " para GET " + url

            with open(file_metadata, 'w') as fp:  # Coloca os dados recebidos para envio em um arquivo
                json.dump( head, fp)

        except Exception as inst:
            logger.exception("Problema tentando baixar o pacote do update")

        now = datetime.datetime.now()
        fpproc.write( str(now) + ' Terminou o download do pacote de update do firmware com resultado : ' + returnmsg)
    if isok:
        os.remove(file_on_process) # indica que deu certo
    return returnmsg


def do_install(tipo):
    if os.path.isfile(file_on_process):
        with open(file_on_process, 'r') as fp:
            err = fp.read(1024)
            return err
    msg = None
    with open(file_on_process, 'w+') as fpproc:
        now = datetime.datetime.now()
        fpproc.write(str(now) + ' Iniciando instalacao do pacote de update do firmware \n')

        if not os.path.isfile(file_metadata) or not os.path.isfile(file_download) :
            msg = "Pacote de update de firmware nao esta disponivel. Primeiro deve ser feito o download."

        head = {}
        if not msg :
            with open(file_metadata, 'r') as fp:  # Coloca os dados recebidos para envio em um arquivo
                head = json.load(fp)

        if not msg :
            now = datetime.datetime.now()
            fpproc.write(str(now) + " Testando a consistencia do pacote. \n")

        if not msg and not 'status' in head :
            msg = "Dados do pacote de update de firmware estao inconsistentes."

        if not msg and ( head['status'] < 200 or head['status'] > 299 ) :
            msg = "Ocorreu problema na tentativa de ler o pacote de update de firmware do servidor."

        if not msg and not 'Content-Length' in head :
            msg = "Dados do pacote de update de firmware estao inconsistentes, falta o tamanho esperado do pacote."

        if not msg :
            expectedsize = int(head['Content-Length'])
            statinfo = os.stat(file_download)
            if expectedsize != statinfo.st_size:
                msg = "O pacote de update de firmware baixado esta inconsistente. Tamanho diferente do esperado."

        if not msg :
            now = datetime.datetime.now()
            fpproc.write(str(now) + " Descompactando o pacote. \n")

        if not msg :
            ## decriptografa o pacote lido
            ac = abs_cript()
            ac.cript(file_download, file_packet, 'volta')

            # ATENCAO     o   "cd /tmp"  eh muito importante
            res = os.system('cd /tmp ; tar zxf ' + file_packet + ' 2>' + file_stderr)
            if res != 0 :   # deu erro
                with open(file_stderr, 'r') as fp:
                    err = fp.read(1024)
                msg = "Falha ao descompactar o pacote.\n" + err

        if not msg :
            now = datetime.datetime.now()
            fpproc.write(str(now) + " Instalando o pacote. \n")

        if not msg :
            res = 0
            if tipo == "install" :
                res = os.system('cd /tmp ; ./instala_nova_remota.sh > ' + file_stderr + ' 2>&1')
            if tipo == "update":
                res = os.system('cd /tmp ; ./update_remota.sh > ' + file_stderr + ' 2>&1')
            if res != 0 :   # deu erro
                with open(file_stderr, 'r') as fp:
                    err = fp.read(1024)
                msg = "Falha na instalacao do update. Problema BEM GRANDE\n" + err

        if not msg :
            msg = "Acompanhe a evolucao da atualizacao pelo log."

        now = datetime.datetime.now()
        fpproc.write(str(now) + ' ' + msg + '\n')
    return msg


def do_read_log(tipo):
    if tipo == 'get_log':
        if os.path.isfile(file_on_process):
            with open(file_on_process, 'r') as fp:
                err = fp.read(10240)
                return err
        if os.path.isfile(file_metadata) and os.path.isfile(file_download):
            with open(file_metadata, 'r') as fp:  # Coloca os dados recebidos para envio em um arquivo
                head = json.load(fp)
                if 199 < head['status'] < 300:
                    return "Pacote baixado. Pode dar o comando de update, ou fazer um novo download.\n"
    elif tipo == 'get_log_script':
        if os.path.isfile(file_stderr):
            with open(file_stderr, 'r') as fp:
                err = fp.read(10240)
                return err
    return "Nenhum processo de update pendente. Pode dar comando de download.\n"


def __do_build_debug_pack(tipo_saida):
    '''
    Recebe
        tipo_saida
            'base64'        montar um arquivo no formato base64 para saida
            None            monta o arquivo criptado
    Retorna
        errcod
            0   tudo correu bem
            1   deu problema no tar
            2   deu problema no cript
            3   deu problema no base64
        filename
            se retorna 0 tambem retorna o nome do arquivo de saida
    '''
    filenametar = '/tmp/download_debug_pach.tar.gz'
    filenamefim = '/tmp/download_debug_pach.celxpack'
    filename64 = '/tmp/download_debug_pach.celxpack.64'
    # chamar o montador do tar para montar o pacote
    cmd = "/abs/montar_tar_download_debug.sh " + filenametar + " >/dev/null 2>&1"
    logger.debug("comando para o tar " + cmd)
    res = os.system(cmd)
    logger.debug("Retorno do tar " + str(res))
    if res != 0:
        return 1, None    #   erro no tar
    ac = abs_cript()
    ac.cript(filenametar, filenamefim, 'vai')
    os.system("rm -f " + filenametar)
    if tipo_saida is None or tipo_saida != 'base64':
        return 0, filenamefim
    cmd = "base64 " + filenamefim + " 2>/dev/null >" + filename64
    res = os.system(cmd)
    logger.debug("Retorno do base64 " + str(res))
    os.system("rm -f " + filenamefim)
    if res != 0:
        return 3, None
    return 0, filename64


def debug_pack_to_cgi():
    return __do_build_debug_pack(None)


def do_build_debug_pack():
    res, file = __do_build_debug_pack('base64')
    if res != 0:
        return "Problemas para montar o pacote"
    conteudo = "Problema enviando o pacote de depuracao"
    if os.path.isfile(file):
        with open(file, 'r') as fp:
            conteudo = fp.read()
    os.system("rm -f " + file)
    return conteudo


def proc( parameters):
    data = parameters['data']
    if data == 'download':
        return do_download(parameters)
    elif data == 'install':
        return do_install(data)
    elif data == 'update':
        return do_install(data)
    elif data == 'get_log':
        return do_read_log(data)
    elif data == 'get_log_script':
        return do_read_log(data)
    elif data == 'get_debug_pack':
        return do_build_debug_pack()
