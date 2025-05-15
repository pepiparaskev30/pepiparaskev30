FROM alpine:3.19

RUN apk add --no-cache stress-ng iperf3 curl bash

COPY load.sh /load.sh
RUN chmod +x /load.sh

CMD ["/load.sh"]
