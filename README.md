# saritasa-pre-commit-hooks

This repository contains special pre-commit hooks that can be reused for Github workflows.

## Hooks available

### `check-nginx-wide-range`

Prevent commiting of nginx wide range configs without `disabled` locations, i.e.

```
# below you can see the example of `wide` nginx config, because files would be searched
# in `$uri` and `$uri/` directories, which can lead to opening of hidden files to the Internet
location / {
  try_files $uri $uri/ /index.php?$query_string;
}

# hook won't raise errors only if there would be defined all below blocks in nginx config (by default)
location ~ \.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$  {deny all;}
location ~ /cron.*                                              {deny all;}
location ~ /\.                                                  {deny all;}
location ~ autodiscover.xml {return 403;}
location ~ apple-touch-icon {return 403;}
location ~ ^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile) {return 403;}
```

#### Examples

1. You can specify custom nginx config file and location `--nginx_config_path=custom.conf`  in case if it is different from `./nginx.conf`

```.pre-commit-config.yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.2
    hooks:
      - id: check-nginx-wide-range
        args:
          - --nginx_config_path=ci/custom.conf
```

2. You can specify extra deny locations in addition to default ones if you need to check repo for some extra disabled locations with `--extra_deny_locations="^/(test/|test1|test2)"` param

Examples:

```.pre-commit-config.yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.2
    hooks:
      - id: check-nginx-wide-range
        args:
          - --extra_deny_locations=^/(test/|test1|test2)
          - --extra_deny_locations=/cron3.*
```

3. You can specify custom deny locations to fully replace default ones if you need to check repo for some other disabled locations with `--custom_deny_locations="/cron2.*"` param

Examples:

```.pre-commit-config.yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.2
    hooks:
      - id: check-nginx-wide-range
        args:
          - --custom_deny_locations=^/(app/|vendor)
          - --custom_deny_locations=/cron2.*
```

Please keep in mind that in case if you messed default locations denies values, hook will ask you to update it to look the same. I.e. when you mixed order of params in `\.(sh|json|conf|xml|md|conf|toml|yml|yaml|log|pid)$` -> you would be forced to update it to this manner `\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$`.

4. You can specify extra keywords, existance of which, will make parser error to be ignored `--ignore_errors_keywords="test"` param

Examples:

```.pre-commit-config.yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.2
    hooks:
      - id: check-nginx-wide-range
        args:
          - --ignore_errors_keywords=test
          - --ignore_errors_keywords=test2
```

Please note that by default there are always ignored errors with these keywords: `fastcgi_params, koi-utf, koi-win, mime.types, scgi_params, uwsgi_params, win-utf`.

Thiey are ignored because sometimes project's nginx config file may contain `include` directives to files without their real presence in the repo (these files are added as [nginx defaults](https://github.com/nginx/nginx/tree/master/conf) during installation) and can be ignored during pre-commit hook processing.

This is it!
