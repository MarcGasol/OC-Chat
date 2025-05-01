我将这个工程起在amazon ec2上

ec2的配置是：
	Ubuntu 22.04
	64-bit (x86) architecture
	Instance type: t2.micro
	Network settings (网络安全组)：允许全部来自0.0.0.0/0的ssh, http, https traffic
	storage: 1 x 8 GiB gp2

建好了ec2 instance 之后拿到.pem结尾的密钥，用这个密钥ssh到ec2机器上开始开发。

开发步骤
1. ssh进入ec2机器，运行 "sudo apt-get update"
2. 运行"sudo apt-get install python3-venv", 下载python虚拟环境的依赖
3. 将工程文件夹scp到ec2的/home/ubuntu 路径下，现在工程文件夹的路径应为/home/ubuntu/adultChat
4. cd进入adultChat，运行"python3 -m venv venv"， 建立针对这个工程的python虚拟环境
5. 运行"source venv/bin/activate"，激活虚拟环境
6. 运行"pip install -r requirements.txt", 下载需要的library
6a. 如果在运行6中指令出现了问题，可以分别运行"pip install Flask"， "pip install gunicorn"， "pip install openai".
7. 运行"gunicorn -b 0.0.0.0:8000 app:app", 确保这样启动服务没有报错。确认之后crtl+c停止服务。
8. 运行"sudo nano /etc/systemd/system/adultChat.service", 写入以下内容，并保存
[Unit]
Description=Gunicorn instance for adultChat (Amanda)
After=network.target
[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/adultChat
ExecStart=/home/ubuntu/adultChat/venv/bin/gunicorn -b localhost:8000 app:app
Restart=always
[Install]
WantedBy=multi-user.target
9. 分别运行"sudo systemctl daemon-reload", "sudo systemctl start adultChat", "sudo systemctl enable adultChat", 这样就用gunicorn在后台启动了服务。
10. 运行 curl localhost:8000 确保能得到非404或者no connection的信息。
11. 运行"sudo apt-get install nginx", 下载nginx.
12. 分别运行 "sudo systemctl start nginx", "sudo systemctl enable nginx", 启动nginx。在本机的chrome浏览器里输入这台ec2的public ip，确保能正常出现nginx的页面
13. 运行"sudo nano /etc/nginx/sites-available/default"，打开nginx的配置文件之后，在 server{listen ...} 的上面（之前）加入
upstream flaskadultChat {
	server 127.0.0.1:8000;
}
接着在server{...} 中找到 location / {...}, 将其中的try_files $uri $uri/ =404; 改为 proxy_pass http://flaskadultChat; 改好之后保存并退出。
14. 运行"sudo systemctl restart nginx",重启nginx。在本机的chrome浏览器上输入这台ec2的public ip，确保能正常出现不是nginx的页面，应该会有类似下面的信息
Hello World the local server time is 2024-10-30 03:15:55.547414 only for adult response
15. 在postman里测试
curl http://PUBLICIP/botResponseFromOC/Nicole -X POST -d '{"convLog":[{"role": "user", "content": "你是谁"}], "summary":"", "model":"qwen-turbo", "user":{"personalKeyInfo":""}}' --header "Content-Type: application/json"

