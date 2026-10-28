#!/bin/sh
#
#   Precompila os pythons que estiverem no sistema para ficar mais rapido
#
# Limpar todos os caches que porventura vieram junto no pacote
find . -name "__pycache__" | while read a; do
  rm -rf $a
done
#
# Agora compilar e ajustar
for pydir in . ; do
    cd $pydir
    python -m compileall .
    dirorig=`pwd`
    # Cria o __pycache__ em cada diretorio
    ## Entrar em cada um deles e
    find . -name "__pycache__" | while read a; do
        echo "### Vai para $a"
        cd $a
        ##       acertar o nome
        for i in *.pyc
        do
            mv $i $(echo $i | cut -f1 -d.).pyc
        done
        ## mover todos os arquivos para o ..
        mv * ..
        ## voltar para o diretorio dos py
        cd ..
        ## remover os .py para deixar de ocupar espaco
        rm -f *.py
        ## Acertar as permissoes
        chmod 644 *.pyc
        ## remover o __pycache__
        rmdir __pycache__
        ## retornar para o diretorio original
        cd $dirorig
    done
done
