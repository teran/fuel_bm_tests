class environment:
      data = {
        "release": 1,
        "mode": "multinode"
      }
      interfaces = {
        'eth0': ["public", "floating"],
        'eth1': ["fixed"],
        'eth2': ["storage", "management"],
        'eth3': ["fuelweb_admin"]
      }
      node_roles = [
        ['controller'],
        ['cinder'],
        ['compute']
      ]
      net_tag = {
         'management': 730,
         'storage': 732,
         'fixed': None
      }
      deploy_timeout = 120 * 60
      settings = {
        "volumes_lvm": True,
	"savanna": True,
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 0
      ostf_timeout = 120 * 60
      ostf_test_sets = ['smoke', 'sanity', 'platform_tests']
      
