TESTS_ENVIRONMENT = export PATH=$(abs_top_srcdir)/tests/tools:$(PATH); export TOPSRCDIR=$(abs_top_srcdir); export GJS_PATH=$(abs_top_srcdir)/logger; export FC_TESTING=true; export XDG_DATA_DIRS=$(abs_top_srcdir)/tests/data/; export PYTHON=@PYTHON@;
TESTS = 00_database.py 00_freeipa.py 00_sshcontroller.py 01_mergers.py 01_logger_dconf.sh 02_logger_connmgr.py 03_logger_nm.py 03_logger_chromium.py 03_logger_firefox.py 04_libvirt_controller.py 05_fcdbus.sh


EXTRA_DIST =                         \
	$(TESTS)                         \
	freeipamock.py                   \
	libvirtmock.py                   \
	_01_mock_dbus.py                 \
	_01_logger_test_suite.py         \
	_01_wait_for_name.py             \
	_05_fcdbus_tests.py              \
	test_fcdbus_service.py           \
	data/test.gschema.xml            \
	data/libvirt_domain-orig.xml     \
	data/libvirt_domain-modified.xml \
	data/libvirt_domain-nospice.xml  \
	data/fc_goa_providers_test.ini   \
	data/fleet-commander-logger/fc-chromium-policies.json   \
	tools/ssh                        \
	tools/ssh-keygen                 \
	tools/ssh-keyscan                \
	tools/ssh-session-mock
