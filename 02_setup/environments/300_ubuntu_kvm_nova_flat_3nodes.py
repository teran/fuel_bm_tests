class environment:
      data = {
        "release": 3,
        "mode": "multinode"
      }
      interfaces = {
        'eth0': ["public", "floating", "storage", "management", "fixed"],
        'eth1': ["fuelweb_admin"]
      }
      special_roles = {}
      node_roles = [
        ['controller'],
        ['cinder'],
        ['compute']
      ]
      net_tag = {
         'management': 471,
         'storage': 472,
         'fixed': 473,
      }
      deploy_timeout = 120 * 60
      settings = {
        "volumes_lvm": True,
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 1
      ostf_timeout = 20 * 60
      ostf_test_sets = ['smoke', 'sanity', 'platform_tests']
      
      net_cidr = {
          'public': "172.18.122.96/28",
          'floating': "172.18.122.96/28",
      }
      net_ip_ranges = {
          'public': [
              [   
                  "172.18.122.105",
                  "172.18.122.107",
              ]
          ],
           'floating': [
              [   

                  "172.18.122.109",
                  "172.18.122.110",
              ]   
           ],
      }
      gateway = None
