





tudo = bytearray("linha1 \nlinha 2 \nlinha 3 \nLinha 4", 'utf-8')


l = bytearray()
for i in tudo :
    if i == 10 :
        print( l.decode('utf-8'))
        l = bytearray()
    else:
        l.append(i)






def separa_log_lines(comando):
    ret = []
    l = ''
    for i in comando :
        if i == "\n":
            ret.append(l)
            l = ''
        else:
            l += i

    return ret


linhas_do_comando = separa_log_lines('1111111 \n222222222\n')

print( str( linhas_do_comando))


def get_next_log_line():
    global linhas_do_comando

    if len(linhas_do_comando) > 0:
        ret = linhas_do_comando[0]
        linhas_do_comando.pop(0)
        return ret
    return None

linha = get_next_log_line()
while linha :
    print(linha)
    linha = get_next_log_line()