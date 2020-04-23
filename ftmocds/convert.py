import logging
from banal import is_mapping, ensure_list
from pprint import pprint  # noqa

from followthemoney import model

log = logging.getLogger(__name__)

DEFTAULT_IDENTIFIER = 'registrationNumber'
IDENTIFIERS = {
    'TRADE_REGISTER': 'registrationNumber',
    'AU-ABN': 'registrationNumber',
    'PY-PGN': 'classification',
    'TAX_ID': 'vatCode',
    'AM-TIN': 'taxNumber',
    'ORGANIZATION_ID': 'classification',
    'STATISTICAL': 'classification',
}
NAMES = ['name', 'legalName', 'entityName', 'businessName',
         'name_hy', 'name_en', 'name_ru', 'name_fr', 'title_en',
         'title_fr', 'title']
DESCRIPTIONS = ['description', 'description_hy', 'description_en',
                'description_ru', 'description_fr']


def clean_date(date):
    if date is not None and 'T' in date:
        date, _ = date.split('T', 1)
    return date


def convert_fields(entity, data, prop, fields):
    if is_mapping(data):
        for field in fields:
            value = data.pop(field, None)
            entity.add(prop, value)


def convert_name(entity, data, prop='name'):
    convert_fields(entity, data, prop, NAMES)


def convert_description(entity, data, prop='summary'):
    convert_fields(entity, data, prop, DESCRIPTIONS)


def convert_identifier(entity, identifier):
    if not is_mapping(identifier):
        entity.add(DEFTAULT_IDENTIFIER, identifier)
        return
    convert_name(entity, identifier)
    scheme = identifier.pop('scheme', None)
    prop = IDENTIFIERS.get(scheme, None)
    if prop is None:
        log.info("Unknown identifier scheme: %s", scheme)
        prop = DEFTAULT_IDENTIFIER
        IDENTIFIERS[scheme] = prop
    entity.add(prop, identifier.pop('id', None))


def convert_value(entity, value):
    if is_mapping(value):
        convert_value(entity, value.pop('amount', None))
        entity.add('currency', value.pop('currency', None))
    else:
        entity.add('amount', value)


def convert_classification(entity, item, prop='classification'):
    if not is_mapping(item):
        entity.add(prop, item)
    else:
        if 'classification' in item:
            convert_classification(entity, item.get('classification'), prop)
        convert_description(entity, item, prop)
        convert_address(entity, item.pop('deliveryAddress', {}))


def convert_address(entity, address):
    if not is_mapping(address):
        entity.add('address', address)
        return
    address.pop('aboriginalRegion', None)
    for addr in ensure_list(address.pop('addresses', [])):
        convert_address(entity, addr)
    entity.add('country', address.pop('countryName', None))
    parts = (address.pop('streetAddress', None),
             address.pop('postalCode', None),
             address.pop('locality', None),
             address.pop('region', None))
    text = ' '.join((str(p) for p in parts if p is not None))
    if len(address):
        log.info("Unknown address part: %r", address.keys())
    entity.add('address', text)


def convert_document(entity, doc):
    if is_mapping(doc):
        entity.add('sourceUrl', doc.get('url'))


def convert_period(entity, period):
    if is_mapping(period):
        entity.add('startDate', period.pop('startDate', None), quiet=True)
        entity.add('endDate', period.pop('endDate', None), quiet=True)


def convert_party(party):
    entity = model.make_entity('LegalEntity')
    party_id = party.pop('id', None)
    identifier = party.pop('identifier', {})
    if party_id is None:
        party_id = identifier.get('id')
    entity.make_id(party_id)
    convert_name(entity, party)
    convert_address(entity, party.pop('address', {}))
    convert_address(entity, party.pop('deliveryAddress', {}))
    entity.add('legalForm', party.pop('organizationType', None))
    contact = party.pop('contactPoint', {})
    entity.add('website', contact.pop('url', None))
    entity.add('phone', contact.pop('telephone', None))
    entity.add('email', contact.pop('email', None))
    convert_identifier(entity, identifier)
    for identifier in party.pop('additionalIdentifiers', []):
        convert_identifier(entity, identifier)
    yield entity
    for mem in ensure_list(party.pop('memberOf', [])):
        for other in convert_party(mem):
            other.schema = model.get('Organization')
            yield other
            mem = model.make_entity('Membership')
            mem.make_id(entity.id, other.id)
            mem.add('member', entity)
            mem.add('organization', other)
            yield mem

    party.pop('roles', None)
    # if len(party):
    #     pprint({'party': party})


def convert_buyer(contract, buyer, country):
    buyer_id = buyer.pop('id', None)
    if buyer_id is not None:
        authority = model.make_entity('LegalEntity')
        authority.make_id(buyer_id)
        convert_name(authority, buyer)
        if authority.has('name'):
            authority.add('country', country)
            contract.add('authority', authority)
            yield authority


def convert_suppliers(ca, supplier):
    for supp in convert_party(supplier):
        ca.add('supplier', supp)
        convert_value(ca, supplier.pop('value', {}))
        convert_value(ca, supplier.pop('awardValue', {}))
        convert_period(ca, supplier.pop('contractPeriod', None))
        yield supp


def convert_item(item, country):
    # pprint(item)
    # return
    tender = item.pop('tender', {})
    contract = model.make_entity('Contract')
    contract_id = item.pop('ocid', item.pop('id', None))
    if contract_id is None:
        return
    contract.make_id(contract_id)
    convert_name(contract, tender, 'title')
    convert_name(contract, item, 'title')
    if not contract.has('title'):
        contract.add('title', tender.get('description'))
    if not contract.has('title'):
        contract.add('title', item.get('description'))
    contract.add('language', tender.pop('language', None))
    contract.add('language', item.pop('language', None))
    convert_description(contract, tender, 'description')
    convert_description(contract, item, 'description')
    contract.add('procedureNumber', tender.pop('id', None))
    contract.add('contractDate', item.pop('date', None))
    contract.add('status', tender.pop('status', None))
    contract.add('method', tender.pop('procurementMethod', None))
    contract.add('method', tender.pop('procurementMethodDetails', None))
    contract.add('method', tender.pop('procurementMethodRationale', None))
    contract.add('method', tender.pop('procurementMethodRationale_en', None))
    contract.add('method', tender.pop('procurementMethodRationale_fr', None))
    contract.add('method', tender.pop('processMethod', None))
    contract.add('criteria', tender.pop('awardCriteria', None))
    contract.add('criteria', tender.pop('awardCriteriaDetails', None))
    contract.add('criteria', tender.pop('awardCriteriaDetails_en', None))
    contract.add('criteria', tender.pop('awardCriteriaDetails_fr', None))
    contract.add('type', tender.pop('mainProcurementCategory', None))
    contract.add('type', tender.pop('tenderType', None))
    convert_address(contract, tender.pop('deliveryAddress', {}))
    convert_value(contract, tender.pop('value', {}))
    convert_value(contract, tender.pop('budget', {}))
    for clazz in ensure_list(tender.pop('items', [])):
        convert_classification(contract, clazz)

    for party in ensure_list(item.pop('parties', [])):
        yield from convert_party(party)

    contracts = ensure_list(item.pop('contracts', {}))
    for cdata in contracts:
        convert_name(contract, cdata, 'title')
        for item in cdata.pop('items', []):
            convert_classification(contract, item)

    for planning in ensure_list(item.pop('planning', {})):
        convert_value(contract, planning.pop('budget', {}))

    buyer = item.pop('buyer', {})
    yield from convert_buyer(contract, buyer, country)

    proc_entity = tender.pop('procuringEntity', {})
    proc_entity_id = proc_entity.pop('id', None)
    if proc_entity_id is not None:
        authority = model.make_entity('LegalEntity')
        authority.make_id(proc_entity_id)
        convert_name(authority, proc_entity)
        if authority.has('name'):
            authority.add('country', country)
            contract.add('authority', authority)
            yield authority

    for doc in tender.pop('documents', []):
        convert_document(contract, doc)
    for doc in item.pop('documents', []):
        convert_document(contract, doc)

    # contract.add('modifiedAt', published_date)
    lots = tender.pop('lots', [])
    awards = item.pop('awards', [])
    for award in ensure_list(awards):
        ca = model.make_entity('ContractAward')
        award_id = award.pop('id', None)
        # pprint({'award': award})
        ca.make_id(contract.id, award_id)
        ca.add('contract', contract)
        ca.add('date', clean_date(award.pop('date', None)))
        ca.add('date', clean_date(award.pop('awardDate', None)))
        convert_value(ca, award.pop('value', {}))
        convert_value(ca, award.pop('totalAwardValue', {}))
        ca.add('status', award.pop('status', None))
        ca.add('role', award.pop('title', None))
        ca.add('summary', award.pop('description', None))
        ca.add('currency', award.pop('currency', None))
        convert_period(ca, award.pop('contractPeriod', None))
        reason = tender.get('procurementMethodDetails', None)
        ca.add('decisionReason', reason)
        contract.add('method', award.pop('procurementMethod', None))
        contract.add('criteria', award.pop('awardCriteria', None))
        buyer = award.pop('buyer', {})
        yield from convert_buyer(contract, buyer, country)

        for document in award.pop('documents', []):
            convert_document(ca, document)

        for cdata in contracts:
            if cdata.get('awardID') == award_id:
                convert_period(ca, cdata.get('period', None))
                convert_value(ca, cdata.pop('value', {}))

        for clazz in award.pop('items', []):
            convert_classification(contract, clazz)
            classification = clazz.pop('classification', {})
            ca.add('cpvCode', classification.get('id'))
            for supplier in ensure_list(clazz.pop('suppliers', [])):
                yield from convert_suppliers(ca, supplier)

        related_lots = ensure_list(award.pop('relatedLots', []))
        for lot in lots:
            if lot.get('id') in related_lots:
                convert_name(ca, lot, 'role')
                convert_description(ca, lot, 'summary')

        for supplier in award.pop('suppliers', []):
            yield from convert_suppliers(ca, supplier)

        # if len(award):
        #     pprint({'award': award})
        # if ca.has('supplier'):
        yield ca

    # if len(tender):
    #     pprint({'tender': tender})
    # if len(item):
    #     pprint({'item': item})
    yield contract


def convert_record(record, country=None):
    published_date = clean_date(record.pop('publishedDate', None))
    publisher = record.pop('publisher', {}).get('name')
    if record.get('tag'):
        for entity in convert_item(record, country):
            entity.add('publisher', publisher, quiet=True)
            entity.add('modifiedAt', published_date, quiet=True)
            yield entity

    compiled_release = record.get('compiledRelease', {})
    for entity in convert_item(compiled_release, country):
        entity.add('publisher', publisher, quiet=True)
        entity.add('modifiedAt', published_date, quiet=True)
        yield entity

    for release in ensure_list(record.get('releases', [])):
        for entity in convert_item(release, country):
            entity.add('publisher', publisher, quiet=True)
            entity.add('modifiedAt', published_date, quiet=True)
            yield entity
