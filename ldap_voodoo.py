import logging
from .conn_manager import LDAPConnectionManager
from addendum.exceptions import LDAPInvalidFullDN

log = logging.getLogger(__name__)
AVAILABLE_LDAP_SCOPE = ('client', 'stuff', 'supervisor', 'sys')

class LDAPWizard(LDAPVoodoo):
    @staticmethod
    def prettify_full_dn(full_dn):
        """
        Made special for @vlados
        :param full_dn: LDAP full_dn
        :return: pretty dict view
        """
        try:
            splatted_full_dn = full_dn.split(",")
            return {
                'cn': splatted_full_dn[0].split("=")[1],
                'dc': splatted_full_dn[-2:],
                'ou': splatted_full_dn[1:-2]
            }
        except Exception as ex:
            raise LDAPInvalidFullDN(ex)
            
    def get_full_dn(self, uid, scope):
        """
        This method will return a list of client dn entries, or None in case that there is no such an entry.
        :param uid: cn to be concatenated to RDN
        :param scope: client|stuff|supervisor
        :return: normalised result or None
        """
        assert scope in AVAILABLE_LDAP_SCOPE
        log.debug('Looking for customer: %s', uid)
        search_result = self.search(base_dn="ou=%s," % scope + self.base_dn,
                                    search_filter="(cn=%s)" % uid,
                                    retrieve_attributes=['dn'])
        try:
            full_dn = search_result[0][0]
        except IndexError:
            raise LDAPInvalidFullDN
        else:
            return {
                'pretty': self.prettify_full_dn(full_dn),
                'normal': full_dn
                }
                
    def get_profile_data(self, full_dn, attributes=None):
        """
        :param full_dn: Distinguished Name (address) of the entry
        :param attributes: List of attribute names
        :return:
        """
        if not isinstance(full_dn, basestring):
            try:
                full_dn = full_dn['normal']
            except KeyError as ex:
                return LDAPInvalidFullDN(ex)
        if isinstance(attributes, (list, tuple)):
            attributes = [attribute.encode("utf-8") for attribute in attributes]
        elif isinstance(attributes, basestring):
            attributes = [attributes.encode("utf-8")]
        else:
            # to retrieve all filled attributes ;)
            attributes = []
        return self.search(base_dn=full_dn, search_filter=None, retrieve_attributes=attributes)
        
    def set_profile_data(self, full_dn, attributes):
        if not isinstance(full_dn, basestring):
            try:
                full_dn = full_dn['normal']
            except KeyError as ex:
                return LDAPInvalidFullDN(ex)
        stringify_attributes = {}
        for key, value in attributes.iteritems():
            # for unicode keys, make them utf8 strings
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            # same thing for values
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            # if it is a list, go through its contents
            elif isinstance(value, list):
                value = [item.encode('utf-8') if isinstance(item, unicode) else item for item in value]
            stringify_attributes[key] = value
        self.modify_attributes(full_dn, attributes)
        
w = LDAPWizard({
                'basedn': 'dc=co,dc=com',
                'user': "cn=admin,dc=co,dc=com",
                'password': "passw0rd",
                'timeout': 3,
                'host': '127.0.0.1',
                'port': 389
            })
print w.get_full_dn('ldap_wizard', 'sys')
