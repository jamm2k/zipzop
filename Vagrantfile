Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  # Exibe a interface gráfica da VM para vermos o erro de inicialização
  config.vm.provider "virtualbox" do |vb|
    vb.gui = true
    vb.memory = "1536"
    vb.cpus = 1
  end

  # Provisionamento comum a todas as VMs
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y python3-pip python3-venv
    
    # Criar virtualenv e instalar dependências
    # Feito fora do /vagrant se houver problemas de symlink no Windows,
    pip3 install -U -r /vagrant/requirements.txt
  SHELL

  config.vm.define "server" do |server|
    server.vm.hostname = "server"
    server.vm.network "private_network", ip: "192.168.56.10"
  end

  config.vm.define "client1" do |client1|
    client1.vm.hostname = "client1"
    client1.vm.network "private_network", ip: "192.168.56.11"
  end

  config.vm.define "client2" do |client2|
    client2.vm.hostname = "client2"
    client2.vm.network "private_network", ip: "192.168.56.12"
  end
end
