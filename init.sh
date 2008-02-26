#!/bin/bash
cd $1
rm -rf working-env
python workingenv.py working-env
source working-env/bin/activate
export NODE=`uname --nodename`
if [ $NODE = "kodos.ccnmtl.columbia.edu" ] || [ $NODE = "monty.ccnmtl.columbia.edu" ]; then
   mv eggs/psycopg2-2.0.6-py2.5-linux-x86_64.egg eggs/psycopg2-2.0.6-py2.5-linux-x86_64.tmp
   mv eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg-64
   mv eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg-32 eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg
fi
easy_install -H None -f eggs eggs/*.egg
if [ $NODE = "kodos.ccnmtl.columbia.edu" ] || [ $NODE = "monty.ccnmtl.columbia.edu" ]; then
   ln -s /usr/lib/python2.5/site-packages/mx/ working-env/lib/python2.5/
   ln -s /usr/lib/python2.5/site-packages/psycopg2/ working-env/lib/python2.5/
   mv eggs/psycopg2-2.0.6-py2.5-linux-x86_64.tmp eggs/psycopg2-2.0.6-py2.5-linux-x86_64.egg
   mv eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg-32
   mv eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg-64 eggs/SilverCity-0.9.7-py2.5-linux-x86_64.egg
fi
