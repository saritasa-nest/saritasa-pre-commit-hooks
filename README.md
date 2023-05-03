# saritasa-pre-commit-hooks

This repository contains special pre-commit hooks that can be reused for Github workflows.

### Hooks available

#### `check-nginx-wide-range`

Prevent commiting of nginx wide range configs without `disabled` locations, i.e.

```
# below you can see the example of `wide` nginx config, because files would be searched
# in `$uri` and `$uri/` directories, which can lead to opening of hidden files to the Internet
location / {
  try_files $uri $uri/ /index.php?$query_string;
}

# hook won't raise errors only if there would be defined all below blocks in nginx config
location ~ \.(json|sh|conf|xml|md|conf|toml|yml|yaml|log|pid)$  {deny all;}
location ~ /cron.*                                              {deny all;}
location ~ /\.                                                  {deny all;}
location ~ autodiscover.xml {return 403;}
location ~ apple-touch-icon {return 403;}
location ~ ^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile) {return 403;}
```

  - You can sepcify custom nginx config file and location `--nginx_config_path=custom.conf`  in case if it is different
  from `./nginx.conf`

Examples:

```.pre-commit-config.yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.1
    hooks:
      - id: check-nginx-wide-range
        # args: [--nginx_config_path, "ci/custom.conf"]
```
