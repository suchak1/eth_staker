if [[ $CI != true ]]; then

  base_yml=$(cat extra/prometheus_base.yml)

  append_write="remote_write:
  - url: https://prometheus-prod-13-prod-us-east-0.grafana.net/api/prom/push
    basic_auth:
      username: ${GRAF_USER}
      password: ${GRAF_PASS}"

  echo "${base_yml}\n${append_write}" > extra/prometheus.yml
fi