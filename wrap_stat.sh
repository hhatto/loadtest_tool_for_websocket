for proc in `ps -aef | grep atta | grep -v grep | awk '{print $2}'`
do
    python stat.py -p $proc &
done


#waitproc=`ps -aef | grep atta | grep -v grep | awk '{print $2}' | tail -n 1`
wait
ps aux | grep atta | grep -v grep
