from collections import defaultdict

from evelink import api, constants
from evelink.parsing.assets import parse_assets
from evelink.parsing.contact_list import parse_contact_list
from evelink.parsing.contract_bids import parse_contract_bids
from evelink.parsing.contract_items import parse_contract_items
from evelink.parsing.contracts import parse_contracts
from evelink.parsing.industry_jobs import parse_industry_jobs
from evelink.parsing.kills import parse_kills
from evelink.parsing.orders import parse_market_orders
from evelink.parsing.wallet_journal import parse_wallet_journal
from evelink.parsing.wallet_transactions import parse_wallet_transactions

class Char(object):
    """Wrapper around /char/ of the EVE API.

    Note that a valid API key is required.
    
    """

    def __init__(self, char_id, api):
        self.api = api
        self.char_id = char_id

    @api.auto_call(
        'char/AssetList', map_params={'char_id': 'characterID'}
    )
    def assets(self, api_result=None):
        """Get information about corp assets.

        Each item is a dict, with keys 'id', 'item_type_id',
        'quantity', 'location_id', 'location_flag', and 'packaged'.
        'location_flag' denotes additional information about the
        item's location; see
        http://wiki.eve-id.net/API_Inventory_Flags for more details.

        If the item corresponds to a container, it will have a key
        'contents', which is itself a list of items in the same format
        (potentially recursively holding containers of its own).  If
        the contents do not have 'location_id's of their own, they
        inherit the 'location_id' of their parent container, for
        convenience.

        At the top level, the result is a dict mapping location ID
        (typically a solar system) to a dict containing a 'contents'
        key, which maps to a list of items.  That is, you can think of
        the top-level values as "containers" with no fields except for
        "contents" and "location_id".
        
        """
        return api.APIResult(parse_assets(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/ContractBids', map_params={'char_id': 'characterID'}
    )
    def contract_bids(self, api_result=None):
        """Lists the latest bids that have been made to any recent auctions."""
        return api.APIResult(parse_contract_bids(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/ContractItems',
        required_params=('contractID',),
        map_params={'char_id': 'characterID'}
    )
    def contract_items(self, contract_id, api_result=None):
        """Lists items that a specified contract contains"""
        return api.APIResult(parse_contract_items(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('char/Contracts', map_params={'char_id': 'characterID'})
    def contracts(self, api_result=None):
        """Returns a record of all contracts for a specified character"""
        return api.APIResult(parse_contracts(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/WalletJournal',
        map_params={
            'char_id': 'characterID',
            'before_id': 'fromID',
            'limit': 'rowCount'
        }
    )
    def wallet_journal(self, before_id=None, limit=None, api_result=None):
        """Returns a complete record of all wallet activity for a specified character"""
        return api.APIResult(parse_wallet_journal(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('char/AccountBalance', map_params={'char_id': 'characterID'})
    def wallet_info(self, api_result=None):
        """Return a given character's wallet."""
        rowset = api_result.result.find('rowset')
        row = rowset.find('row')
        result = {
            'balance': float(row.attrib['balance']),
            'id': int(row.attrib['accountID']),
            'key': int(row.attrib['accountKey']),
        }
        return api.APIResult(result, api_result.timestamp, api_result.expires)

    def wallet_balance(self):
        """Helper to return just the balance from a given character wallet"""
        api_result = self.wallet_info()
        return api.APIResult(api_result.result['balance'], api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/WalletTransactions',
        map_params={
            'char_id': 'characterID',
            'before_id': 'fromID',
            'limit': 'rowCount'
        }
    )
    def wallet_transactions(self, before_id=None, limit=None, api_result=None):
        """Returns wallet transactions for a character."""
        return api.APIResult(parse_wallet_transactions(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/IndustryJobs', map_params={'char_id': 'characterID'}
    )
    def industry_jobs(self, api_result=None):
        """Get a list of jobs for a character"""
        return api.APIResult(parse_industry_jobs(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/KillLog',
        map_params={'char_id': 'characterID', 'before_kill': 'beforeKillID'}
    )
    def kills(self, before_kill=None, api_result=None):
        """Look up recent kills for a character.

        before_kill:
            Optional. Only show kills before this kill id. (Used for paging.)

        """
        return api.APIResult(parse_kills(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/Notifications', map_params={'char_id': 'characterID'}
    )
    def notifications(self, api_result=None):
        """Returns the message headers for notifications."""
        result = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            notification_id = int(a['notificationID'])
            result[notification_id] = {
                'id': notification_id,
                'type_id': int(a['typeID']),
                'sender_id': int(a['senderID']),
                'timestamp': api.parse_ts(a['sentDate']),
                'read': a['read'] == '1',
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/NotificationTexts',
        required_params=('IDs',),
        map_params={'char_id': 'characterID'}
    )
    def notification_texts(self, notification_ids, api_result=None):
        """Returns the message bodies for notifications."""
        result = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            notification_id = int(row.attrib['notificationID'])
            notification = {'id': notification_id}
            notification.update(api.parse_keyval_data(row.text))
            result[notification_id] = notification

        missing_ids = api_result.result.find('missingIDs')
        if missing_ids is not None:
            for missing_id in missing_ids.text.split(","):
                result[missing_id] = None

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/Standings',
        map_params={'char_id': 'characterID'}
    )
    def standings(self, api_result=None):
        """Returns the standings towards a character from NPC entities."""
        result = {}
        rowsets = {}
        for rowset in api_result.result.find('characterNPCStandings').findall('rowset'):
            rowsets[rowset.attrib['name']] = rowset

        _name_map = {
            'agents': 'agents',
            'corps': 'NPCCorporations',
            'factions': 'factions',
        }

        for key, rowset_name in _name_map.iteritems():
            result[key] = {}
            for row in rowsets[rowset_name].findall('row'):
                a = row.attrib
                from_id = int(a['fromID'])
                result[key][from_id] = {
                    'id': from_id,
                    'name': a['fromName'],
                    'standing': float(a['standing']),
                }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/CharacterSheet', 
        map_params={'char_id': 'characterID'}
    )
    def character_sheet(self, api_result=None):
        """Returns attributes relating to a specific character."""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)
        result = {
            'id': _int('characterID'),
            'name': _str('name'),
            'create_ts': _ts('DoB'),
            'race': _str('race'),
            'bloodline': _str('bloodLine'),
            'ancestry': _str('ancestry'),
            'gender': _str('gender'),
            'corp': {
                'id': _int('corporationID'),
                'name': _str('corporationName'),
            },
            'alliance': {
                'id': _int('allianceID') or None,
                'name': _str('allianceName'),
            },
            'clone': {
                'name': _str('cloneName'),
                'skillpoints': _int('cloneSkillPoints'),
            },
            'balance': _float('balance'),
            'attributes': {},
        }

        for attr in ('intelligence', 'memory', 'charisma', 'perception', 'willpower'):
            result['attributes'][attr] = {}
            base = int(api_result.result.findtext('attributes/%s' % attr))
            result['attributes'][attr]['base'] = base
            result['attributes'][attr]['total'] = base
            bonus = api_result.result.find('attributeEnhancers/%sBonus' % attr)
            if bonus is not None:
                mod = int(bonus.findtext('augmentatorValue'))
                result['attributes'][attr]['total'] += mod
                result['attributes'][attr]['bonus'] = {
                    'name': bonus.findtext('augmentatorName'),
                    'value': mod,
                }

        rowsets = {}
        for rowset in api_result.result.findall('rowset'):
            key = rowset.attrib['name']
            rowsets[key] = rowset

        result['skills'] = []
        result['skillpoints'] = 0
        for skill in rowsets['skills']:
            a = skill.attrib
            sp = int(a['skillpoints'])
            result['skills'].append({
                'id': int(a['typeID']),
                'skillpoints': sp,
                'level': int(a['level']),
                'published': a['published'] == '1',
            })
            result['skillpoints'] += sp

        result['certificates'] = set()
        for cert in rowsets['certificates']:
            result['certificates'].add(int(cert.attrib['certificateID']))

        result['roles'] = {}
        for our_role, ccp_role in constants.Char().corp_roles.iteritems():
            result['roles'][our_role] = {}
            for role in rowsets[ccp_role]:
                a = role.attrib
                role_id = int(a['roleID'])
                result['roles'][our_role][role_id] = {
                    'id': role_id,
                    'name': a['roleName'],
                }

        result['titles'] = {}
        for title in rowsets['corporationTitles']:
            a = title.attrib
            title_id = int(a['titleID'])
            result['titles'][title_id] = {
                'id': title_id,
                'name': a['titleName'],
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/ContactList',
        map_params={'char_id': 'characterID'}
    )
    def contacts(self, api_result=None):
        """Return a character's personal, corp and alliance contact lists."""
        return api.APIResult(parse_contact_list(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('char/MarketOrders', map_params={'char_id': 'characterID'})
    def orders(self, api_result=None):
        """Return a given character's buy and sell orders."""
        return api.APIResult(parse_market_orders(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('char/Research', map_params={'char_id': 'characterID'})
    def research(self, api_result=None):
        """Returns information about the agents with whom the character is doing research."""
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')
        result = {}
        for row in rows:
            a = row.attrib
            id = int(a['agentID'])
            result[id] = {
                'id': id,
                'skill_id': int(a['skillTypeID']),
                'timestamp': api.parse_ts(a['researchStartDate']),
                'per_day': float(a['pointsPerDay']),
                'remaining': float(a['remainderPoints']),
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/SkillInTraining', map_params={'char_id': 'characterID'}
    )
    def current_training(self, api_result=None):
        """Returns the skill that is currently being trained by a specified character"""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)
        result = {
            'start_ts': _ts('trainingStartTime'),
            'end_ts': _ts('trainingEndTime'),
            'type_id': _int('trainingTypeID'),
            'start_sp': _int('trainingStartSP'),
            'end_sp': _int('trainingDestinationSP'),
            'current_ts': _ts('currentTQTime'),
            'level': _int('trainingToLevel'),
            'active': _bool('skillInTraining'),
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('char/SkillQueue', map_params={'char_id': 'characterID'})
    def skill_queue(self, api_result=None):
        """returns the skill queue of the character"""
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')
        result = []
        for row in rows:
            a = row.attrib
            line = {
                'position': int(a['queuePosition']),
                'type_id': int(a['typeID']),
                'level': int(a['level']),
                'start_sp': int(a['startSP']),
                'end_sp': int(a['endSP']),
                'start_ts': api.parse_ts(a['startTime']),
                'end_ts': api.parse_ts(a['endTime']),
            }

            result.append(line)

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('char/MailMessages', map_params={'char_id': 'characterID'})
    def messages(self, api_result=None):
        """Returns a list of headers for a character's mail."""
        rowset = api_result.result.find('rowset')
        results = []
        for row in rowset.findall('row'):
            a = row.attrib
            message = {
                'id': int(a['messageID']),
                'sender_id': int(a['senderID']),
                'timestamp': api.parse_ts(a['sentDate']),
                'title': a['title'],
                'to': {},
            }

            org_id = a['toCorpOrAllianceID']
            message['to']['org_id'] = int(org_id) if org_id else None

            char_ids = a['toCharacterIDs']
            message['to']['char_ids'] = [int(i) for i in char_ids.split(',')] if char_ids else None

            list_ids = a['toListID']
            message['to']['list_ids'] = [int(i) for i in list_ids.split(',')] if list_ids else None

            results.append(message)

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/MailBodies',
        required_params=('ids',),
        map_params={'char_id': 'characterID'}
    )
    def message_bodies(self, message_ids, api_result=None):
        """Returns the actual body content of a set of mail messages.

        NOTE: You *must* have recently looked up the headers of
        any messages you are requesting bodies for (via the 'messages'
        method) or else this call will fail.

        """
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            message_id = int(row.attrib['messageID'])
            results[message_id] = row.text

        missing_set = api_result.result.find('missingMessageIDs')
        if missing_set is not None:
            missing_ids = [int(i) for i in missing_set.text.split(',')]
            for missing_id in missing_ids:
                results[missing_id] = None

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('char/MailingLists', map_params={'char_id': 'characterID'})
    def mailing_lists(self, api_result=None):
        """Returns the mailing lists to which a character is subscribed."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            results[int(a['listID'])] = a['displayName']

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/UpcomingCalendarEvents', map_params={'char_id': 'characterID'}
    )
    def calendar_events(self, api_result=None):
        """Returns the list of upcoming calendar events for a character."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            event = {
                'id': int(a['eventID']),
                'owner': {
                    'id': int(a['ownerID']),
                    'name': a['ownerName'] or None,
                },
                'start_ts': api.parse_ts(a['eventDate']),
                'title': a['eventTitle'],
                'duration': int(a['duration']),
                'important': a['importance'] == '1',
                'description': a['eventText'],
                'response': a['response'],
            }
            results[event['id']] = event

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/CalendarEventAttendees',
        required_params=('eventIDs',),
        map_params={'char_id': 'characterID'}
    )
    def calendar_attendees(self, event_ids, api_result=None):
        """Returns the list of attendees for the specified calendar event.

        This function takes a list of event IDs and returns a dict of dicts,
        with the top-level dict being keyed by event ID and the children
        keyed by the character IDs of the attendees.

        NOTE: You must have recently fetched the list of calendar events
        (using the 'calendar_events' method) before calling this method.

        """
        results = defaultdict(dict, ((id_, {},) for id_ in event_ids))
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            attendee = {
                'id': int(a['characterID']),
                'name': a['characterName'],
                'response': a['response'],
            }
            results[int(a['eventID'])][attendee['id']] = attendee

        return api.APIResult(dict(results), api_result.timestamp, api_result.expires)

    def event_attendees(self, event_id, api_result=None):
        """Returns the attendees for a single event.

        (This is a convenience wrapper around 'calendar_attendees'.)

        NOTE: You must have recently fetched the list of calendar events
        (using the 'calendar_events' method) before calling this method.

        """
        api_result = self.calendar_attendees([event_id])
        return api.APIResult(api_result.result[int(event_id)], api_result.timestamp, api_result.expires)

    @api.auto_call('char/FacWarStats', map_params={'char_id': 'characterID'})
    def faction_warfare_stats(self, api_result=None):
        """Returns FW stats for this character, if enrolled in FW.

        NOTE: This will return an error instead if the character
        is not enrolled in Faction Warfare.

        """
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        result = {
            'faction': {
                'id': _int('factionID'),
                'name': _str('factionName'),
            },
            'enlist_ts': _ts('enlisted'),
            'rank': {
                'current': _int('currentRank'),
                'highest': _int('highestRank'),
            },
            'kills': {
                'yesterday': _int('killsYesterday'),
                'week': _int('killsLastWeek'),
                'total': _int('killsTotal'),
            },
            'points': {
                'yesterday': _int('victoryPointsYesterday'),
                'week': _int('victoryPointsLastWeek'),
                'total': _int('victoryPointsTotal'),
            },
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('char/Medals', map_params={'char_id': 'characterID'})
    def medals(self, api_result=None):
        """Returns a list of medals the character has."""
        result = {'current': {}, 'other': {}}
        _map = {
            'currentCorporation': 'current',
            'otherCorporations': 'other',
        }

        for rowset in api_result.result.findall('rowset'):
            name = _map[rowset.attrib['name']]
            for row in rowset.findall('row'):
                a = row.attrib
                medal_id = int(a['medalID'])
                result[name][medal_id] = {
                    'id': medal_id,
                    'reason': a['reason'],
                    'public': a['status'] == 'public',
                    'issuer_id': int(a['issuerID']),
                    'corp_id': int(a['corporationID']),
                    'title': a['title'],
                    'description': a['description'],
                }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/ContactNotifications', map_params={'char_id': 'characterID'}
    )
    def contact_notifications(self, api_result=None):
        """Returns pending contact notifications."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            note = {
                'id': int(a['notificationID']),
                'sender': {
                    'id': int(a['senderID']),
                    'name': a['senderName'],
                },
                'timestamp': api.parse_ts(a['sentDate']),
                'data': api.parse_keyval_data(a['messageData']),
            }
            results[note['id']] = note

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call(
        'char/Locations',
        required_params=('IDs',),
        map_params={'char_id': 'characterID'}
    )
    def locations(self, location_list, api_result=None):
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            name = row.attrib['itemName'] or None
            id = int(row.attrib['itemID']) or None
            x = float(row.attrib['x']) or None
            y = float(row.attrib['y']) or None
            z = float(row.attrib['z']) or None

            results[id] = {
                'name': name,
                'id' : id,
                'x' : x,
                'y' : y,
                'z' : z,
            }
        return api.APIResult(results, api_result.timestamp, api_result.expires)


# vim: set ts=4 sts=4 sw=4 et:
