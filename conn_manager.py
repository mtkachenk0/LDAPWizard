"""
LDAP-related python-objects
"""
import logging
import ldap
import ldap.modlist

log = logging.getLogger(__name__)


class LDAPConnectionManager(object):
    """
    Simple LDAP Connection object
    """

    def __init__(self, ldap_configs):
        """
        Initialise simple LDAP connection
        and store all necessary ldap data
        :param ldap_configs: dict configs
        """
        assert isinstance(ldap_configs, dict)
        try:
            self.base_dn = ldap_configs['basedn']
            self.host = ldap_configs['host']
            self.port = ldap_configs['port']
            self.user = ldap_configs['user']
            self.password = ldap_configs['password']
            self.timeout = ldap_configs['timeout']
        except KeyError as ex:
            raise IOError("Can not find %s in %s, aborting" % (ex, ldap_configs))
        self.connection = None
        self.connection = self.connect()
        # log.debug("Created new LDAPConnection instance %s" % self)

    def get_connection(self):
        """
        Initialise connection to LDAP if not exists
        :return: connection to LDAP
        """
        if not self.connection:
            # log.debug("Initialized new LDAPConnection")
            new_conn = ldap.initialize("ldap://%s:%s" % (self.host, self.port))
            self.connection = new_conn

        return self.connection

    def disconnect(self):
        """
        Disconnect from LDAP, clear self.connection object
        :return: None
        """
        log.debug("Disconnecting %s" % self)
        self.connection.unbind_s()
        self.connection = None

    def connect(self):
        """

        :return:
        """
        established_connection = self.get_connection()
        # Set timeout options.
        # As I understand only OPT_TIMEOUT is of any use
        established_connection.set_option(ldap.OPT_TIMELIMIT, int(self.timeout))  # Must be int
        established_connection.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)  # May be float
        established_connection.set_option(ldap.OPT_TIMEOUT, self.timeout)  # May be float

        try:
            established_connection.protocol_version = ldap.VERSION3
            established_connection.simple_bind_s(self.user, self.password)
            log.debug("New LDAP connection to %s:%s established, user %s" % (self.host, self.port, self.user))
            # add connection class to connections and set the value to False, that means it's busy
            return established_connection

        except ldap.LDAPError as ex:
            log.error(
                "Failed to open new connection to LDAP %s:%s, user %s.\n%s" % (self.host, self.port, self.user, ex)
            )
            raise


class LDAPVoodoo(LDAPConnectionManager):

    def search(self, base_dn, search_filter=None, scope=ldap.SCOPE_SUBTREE, retrieve_attributes=None):
        """
        Perform LDAP search.
        May throw ldap_utils exceptions or OutOfConnections
        :param base_dn: base_dn to be found in LDAP
        :param search_filter: filter to sort search [DEFAULT = None]
        :param scope: relative DN to search in
        :param retrieve_attributes: attributes to be retrieved [DEFAULT = None]
        :return: search result.
        """
        if search_filter is None:
            parts = base_dn.split(',', 1)
            if len(parts) == 2:
                search_filter, base_dn = parts
            else:
                search_filter = parts[0]
                base_dn = ""
        try:
            log.debug(
                "base_dn = %s, scope = %s, search_filter = %s, retrieve_attributes = %s" % (
                    base_dn, scope, search_filter, retrieve_attributes)
            )
            data = self.connection.search_s(base_dn, scope, search_filter, retrieve_attributes)
            return data
        except (ldap.TIMEOUT, ldap.SERVER_DOWN):
            # Reconnecting
            self.disconnect()
            self.connection = self.connect()
            log.debug("(2nd attempt) Searched for attribute(s) of LDAP base DN %s, filter %s" % (
                base_dn, search_filter)
                      )
            return self.connection.search_s(base_dn, scope, search_filter, retrieve_attributes)
        except Exception as ex:
            log.exception("Unexpected exception %s " % ex)
            raise

    def delete_entry(self, dn):
        """
        Delete the node with all of its attributes.
        Needless to say, the node must exist.
        Or else.
        :param dn: fullDN of the entry that should be deleted from LDAP tree
        """
        try:
            # raw_input("Press Enter to continue...")
            self.connection.delete_s(dn)
        except ldap.TIMEOUT:
            # Try once more, pass the exception to the caller if faled
            self.disconnect()
            self.connection = self.connect()
            self.connection.delete_s(dn)
        log.info("Deleted LDAP node %s" % dn)

    def create_entry(self, dn, attributes):
        """
        :param dn: new entry's full_dn
        :param attributes: attributes to be filled
        :return: None
        """
        if not isinstance(attributes, dict):
            raise TypeError("Expected type dict() for arguments, got %s instead" % type(attributes))

        ldif = ldap.modlist.addModlist(attributes)
        log.info('console log :D')
        try:
            log.debug(dn)
            self.connection.add_s(dn, ldif)
        except ldap.TIMEOUT as ex:
            # Try once more, pass the exception to the caller if failed
            log.warning(ex)
            self.disconnect()
            self.connection = self.connect()
            self.connection.add_s(dn, attributes)
        except ldap.ALREADY_EXISTS:
            log.warning("Entry <%s> already exists" % dn)
        log.info("Added LDAP node %s" % dn)

    def modify_attributes(self, dn, attributes, create=False):
        """
        :param dn: new entry's full_dn
        :param attributes: attributes to be filled
        :param create: if create is False, the attributes will be MODIFIED,
            if it is true, they will be ADDED to the node
        :return: original ldap.modify_s returns query id, I think it's useless,
            therefore this method will return nothing
        """
        if create:
            operation = ldap.MOD_ADD
        else:
            operation = ldap.MOD_REPLACE

        modlist = []
        for k, v in attributes.iteritems():
            if isinstance(v, list):
                raise (RuntimeError, "This will not work with list values")
            if v:
                modlist.append((operation, k, v))

        log.debug("Modlist: %s" % modlist)
        try:
            log.debug('%s, %s' % (dn, type(dn)))
            self.connection.modify_s(dn, modlist)
        except ldap.TIMEOUT as ex:
            # Try once more, pass the exception to the caller if faled
            self.disconnect()
            self.connection = self.connect()
            self.connection.modify_s(dn, modlist)
        except ldap.INVALID_SYNTAX as ex:
            log.exception(ex)
            self.connection.modify_s(dn, modlist)
        log.debug("Modified attribute(s) of LDAP node {0}".format(dn))


if __name__ == '__main__':
    # HOW_TO
    # Create an instance of LDAPConnectionManager
    def test_govnocode():
        c = LDAPVoodoo(
            {
                'basedn': 'dc=co,dc=com',
                'user': "cn=admin,dc=co,dc=com",
                'password': "passw0rd",
                'timeout': 3,
                'host': '127.0.0.1',
                'port': 389
            })
        # SEARCH ENTRY
        found = c.search(base_dn="ou=sys,dc=co,dc=com")
        print found

        CN = "test"
        DN = "cn=%s,ou=sys,dc=co,dc=com" % CN

        on_create_attributes = dict().fromkeys(("cn", "sn", "uid", "userPassword"), CN)
        on_create_attributes['objectClass'] = ['inetOrgPerson', 'organizationalPerson', 'person', 'top']
        # ADD ENTRY
        print "Going to create the entry"
        c.create_entry(dn=DN, attributes=on_create_attributes)
        # MODIFY ENTRY
        print "Going to update the entry"
        on_modify_attributes = dict().fromkeys(("description", "mail"), "test1@gmail.com")
        c.modify_attributes(dn=DN, attributes=on_modify_attributes, create=False)
        c.delete_entry(dn=DN)

        #print c1
        #print c1.__dict__
        #print c1.connections
        #print c1.close_all_connections()
        #print c1.connections
    import time
    started = time.time()
    test_govnocode()
    print "Total elapsed time: %s" % (time.time() - started)
