rabbitmqctl add_vhost filedhost && rabbitmqctl add_user filed filed && rabbitmqctl set_permissions -p filedhost filed ".*" ".*" ".*" && rabbitmqctl set_user_tags filed administrator

