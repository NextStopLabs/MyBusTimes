# MyBusTimes  

## Linux Prod Setup - Bash
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash - 
sudo apt install -y nodejs git python3 python3-venv
```

```bash
git clone https://github.com/Kai-codin/MyBusTimes.git
```

```bash
cd MyBusTimes
```

```bash
chmod +x setup.sh run.sh
```

```bash
./setup.sh
```

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Linux Dev Setup - Bash
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash - 
sudo apt install -y nodejs git python3 python3-venv
```

```bash
git clone https://github.com/Kai-codin/MyBusTimes.git
```

```bash
cd MyBusTimes
```

```bash
chmod +x setup.sh run.sh
```

```bash
./setup.sh
```

```bash
./run.sh
```

## Windows Setup  
```bash
git clone https://github.com/Kai-codin/MyBusTimes.git
```

```bash
cd MyBusTimes
```

```bash
setup.bat
```

```bash
run.bat
```