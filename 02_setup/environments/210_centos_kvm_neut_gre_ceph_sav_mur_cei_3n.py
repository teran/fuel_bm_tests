class environment:
      data = {
        "release": 1,
        "mode": "multinode"
      }
      interfaces = {
        'eth0': ["public", "storage", "management", "private"],
        'eth1': ["fuelweb_admin"]
      }
      special_roles = {}
      node_roles = [
        ['controller', 'ceph-osd'],
        ['cinder', 'ceph-osd'],
        ['compute', 'ceph-osd']
      ]
      net_tag = {
         'management': 471,
         'storage': 472
      }
      deploy_timeout = 120 * 60
      settings = {
        "volumes_lvm": False,
        "volumes_ceph": True,
        "images_ceph": True,
        "murano": True,
        "savanna": True,
        "ceilometer": True,
        "net_provider": 'neutron',
        "net_segment_type": 'gre',
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 11
      ostf_timeout = 6 * 60 * 60
      ostf_test_sets = ['smoke', 'sanity', 'platform_tests']
      
      net_cidr = {
          'public': "172.18.122.96/28"
      }
      net_ip_ranges = {
          'public': [
              [   
                  "172.18.122.105",
                  "172.18.122.107"
              ]
           ],
           'net04_ext': [
                  "172.18.122.109",
                  "172.18.122.110"
           ],
      }
      gateway = None
