FROM alpine:latest

RUN apk update && \
    apk add libteam && \
    apk add open-lldp && \
    apk add sudo && \
    apk add tcpdump && \
    apk add scapy && \
    apk add iperf3 && \
    apk add openssh && \
    apk add openssh-server-pam


RUN adduser -u 1000 -G wheel -s /bin/sh -D alpine && \
    echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

COPY sshd_config /etc/ssh/sshd_config
RUN mkdir /home/alpine/.ssh
COPY demo.key.pub /home/alpine/.ssh/authorized_keys
RUN chown -R alpine /home/alpine/.ssh && chmod 700 /home/alpine/.ssh && chmod 600 /home/alpine/.ssh/authorized_keys

COPY entrypoint.sh /home/alpine/
RUN chmod +x /home/alpine/entrypoint.sh

USER alpine
EXPOSE 22
ENTRYPOINT ["/home/alpine/entrypoint.sh"]
CMD []
