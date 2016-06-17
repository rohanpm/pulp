# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

NFS_VERSION = ENV['PULP_NFS_VERSION'] ? ENV['PULP_NFS_VERSION'].to_i : 4

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
 # It is possible to use URLs to nightly images produced by the Fedora project here. You can find
 # the nightly composes here: https://kojipkgs.fedoraproject.org/compose/
 # Sometimes, a nightly compose is incomplete and does not contain a Vagrant image, so you may need
 # to browse that repository a bit to find the latest successful Vagrant image. For example, at the
 # time of this writing, I could set this setting like this for the latest F24 image:
 # config.vm.box = "https://kojipkgs.fedoraproject.org/compose/24/Fedora-24-20160430.0/compose/CloudImages/x86_64/images/Fedora-Cloud-Base-Vagrant-24_Beta-1.4.x86_64.vagrant-libvirt.box"
 config.vm.box = "fedora/23-cloud-base"

 config.vm.provider 'docker' do |d, override|
  override.vm.box = nil

  d.build_dir = 'playpen/vagrant-base'
  d.has_ssh = true

  # necessary for systemd to work
  d.privileged = true

  override.vm.synced_folder ".", "/vagrant", type: nil
  override.vm.synced_folder "..", "/home/vagrant/devel", type: nil
 end

#    # Reset the UID and GID of the vagrant user in the container equal to the
#    # UID/GID on the host.  This makes it much easier to deal with the
#    # permissions on shared directories.
#    #
#    # This is only needed for docker, so it's declared here in the docker
#    # provider.  Note it actually runs _after_ the ansible provisioner later
#    # declared, since vagrant by design applies configuration from outside-in.
#    #
#    # This is a shell provisioner because it's impractical to apply it using
#    # ansible due to peculiar requirements: you cannot 'usermod' a user if that
#    # user has any processes currently running - including the ssh session that
#    # vagrant itself uses to connect to the container.
#    override.vm.provision 'reset-user', :type => 'shell' do |shell|
#      uid = Process.euid
#      gid = Process.egid
#      reset_cmd = "/vagrant/misc/reset-vagrant-user #{uid} #{gid}"
#
#      shell.inline = <<-END_SCRIPT.gsub(/\s+/, ' ').strip
#        nohup sudo /bin/sh -c '
#          if ! #{reset_cmd}; then
#            wall "About to kill all vagrant processes for UID reassign!";
#            sleep 2;
#            pkill -TERM -u vagrant;
#            sleep 1;
#            pkill -KILL -u vagrant;
#            #{reset_cmd};
#          fi
#        ' >/tmp/reset-user.log 2>&1 &
#      END_SCRIPT
#
#      shell.privileged = false
#    end

 # By default, Vagrant wants to mount the code in /vagrant with NFSv3, which will fail. Let's
 # explicitly mount the code using NFSv4.
 config.vm.synced_folder ".", "/vagrant", type: "nfs", nfs_version: NFS_VERSION, nfs_udp: false

 # You can speed up package installs in subsequent "vagrant up" operations by making the dnf
 # cache a synced folder. This is essentially what the vagrant-cachier plugin would do for us
 # if it supported dnf, and unfortunately that project is in need of maintainers so this might
 # be the best we can do for now. Note that you'll have to manually create the '.dnf-cache'
 # directory in the same directory as this Vagrantfile for this to work.
 # config.vm.synced_folder ".dnf-cache", "/var/cache/dnf", type: "nfs", nfs_version: 4, nfs_udp: false

 # Comment out if you don't want Vagrant to add and remove entries from /etc/hosts for each VM.
 # requires the vagrant-hostmanager plugin to be installed
 if Vagrant.has_plugin?("vagrant-hostmanager")
     config.hostmanager.enabled = true
     config.hostmanager.manage_host = true
 end

 # Comment this line if you would like to disable the automatic update during provisioning
 config.vm.provision "shell", inline: "sudo dnf upgrade -y"

 # bootstrap and run with ansible
 config.vm.provision "shell", path: "playpen/bootstrap-ansible.sh"
 config.vm.provision "ansible" do |ansible|
     # Uncomment this if you want debug tools like gdb, tcpdump, et al. installed
     # (you don't, unless you know you do)
     # ansible.extra_vars = { pulp_dev_debug: true }
     ansible.playbook = "playpen/ansible/vagrant-playbook.yml"
 end

 # Create the "dev" box
 config.vm.define "dev" do |dev|
    dev.vm.host_name = "dev.example.com"

    dev.vm.synced_folder "..", "/home/vagrant/devel", type: "nfs", nfs_version: NFS_VERSION, nfs_udp: false

    dev.vm.provider :libvirt do |domain|
        domain.cpus = 2
        domain.graphics_type = "spice"
        domain.memory = 1024
        domain.video_type = "qxl"

        # Uncomment this to expand the disk to the given size, in GB (default is usually 40)
        # You'll also need to uncomment the provisioning step below that resizes the root partition
        # do not set this to a size smaller than the base box, or you will be very sad
        # domain.machine_virtual_size = 80

        # Uncomment the following line if you would like to enable libvirt's unsafe cache
        # mode. It is called unsafe for a reason, as it causes the virtual host to ignore all
        # fsync() calls from the guest. Only do this if you are comfortable with the possibility of
        # your development guest becoming corrupted (in which case you should only need to do a
        # vagrant destroy and vagrant up to get a new one).
        #
        # domain.volume_cache = "unsafe"
    end

    # Uncomment this to resize the root partition and filesystem to fill the base box disk
    # This script is only guaranteed to work with the default official fedora image, and is
    # only needed it you changed machine_virtual_size above.
    # For other boxen, use at your own risk
    # dev.vm.provision "shell", path: "playpen/vagrant-resize-disk.sh"

    dev.vm.provision "shell", inline: "sudo -u vagrant bash /home/vagrant/devel/pulp/playpen/vagrant-setup.sh"
 end
end
