for i in `docker ps -a | awk '(NR>1) {print $1}'`; do docker rm $i ; done
