for i in `docker ps | awk '(NR>1) {print $1}'`; do docker stop $i ; done
