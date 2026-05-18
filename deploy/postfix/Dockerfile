# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk postfix + opendkim 통합 image — Phase 4 SMTP.
# 한글 주석: Debian slim base + postfix + opendkim sidecar 통합 + SPF/DKIM/DMARC 정합.
# OTP 발송 + Let's Encrypt TLS + KST timezone 의무.

FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

# 한글 주석: postfix + opendkim + ca-certs + supervisor + tzdata.
# postfix 의 init 의 hostname 의무 = MAILDOMAIN env 의 entrypoint 처리.
RUN apt-get update && apt-get install -y --no-install-recommends \
      postfix \
      postfix-mysql \
      opendkim \
      opendkim-tools \
      ca-certificates \
      supervisor \
      tzdata \
      bsd-mailx \
    && rm -rf /var/lib/apt/lists/* \
    && cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone

# 한글 주석: opendkim user + postfix user (opendkim group 추가)
RUN usermod -a -G opendkim postfix

# postfix 본 설정 + opendkim socket + supervisor entry
COPY main.cf /etc/postfix/main.cf
COPY master.cf /etc/postfix/master.cf
COPY opendkim.conf /etc/opendkim.conf
COPY opendkim/KeyTable /etc/opendkim/KeyTable
COPY opendkim/SigningTable /etc/opendkim/SigningTable
COPY opendkim/TrustedHosts /etc/opendkim/TrustedHosts
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && mkdir -p /var/spool/postfix /var/log/supervisor /run/opendkim \
    && chown opendkim:opendkim /run/opendkim

EXPOSE 25 587

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
