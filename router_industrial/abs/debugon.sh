#!/bin/sh

echo "ABS_LOG_KIND='full'" > /usr/lib/python3.6/debug_env.py
chmod 644 /usr/lib/python3.6/debug_env.py
/etc/init.d/abs_conversor restart
/etc/init.d/abs_status_config restart
