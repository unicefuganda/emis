from rapidsms_xforms.models import XForm, XFormField, XFormFieldConstraint
from poll.models import Poll
from script.models import Script, ScriptStep
from rapidsms_xforms.models import XFormSubmission, XFormSubmissionValue
from django.db.models import Count, Sum

try:
    from django.contrib.sites import Site
except ImportError:
    pass


GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

months = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sept',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec'
}

quarters = {
    1:'First',
    2:'Second',
    3:'Third',
    4:'Forth'
}

GROUP_BY_SELECTS = {
    GROUP_BY_DAY:('day', 'date(rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_WEEK:('week', 'extract(week from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_MONTH:('month', 'extract(month from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_QUARTER:('quarter', 'extract(quarter from rapidsms_xforms_xformsubmission.created)',),
}


def total_submissions(keyword, start_date, end_date, location, extra_filters=None, group_by_timespan=None):
    if extra_filters:
        extra_filters = dict([(str(k), v) for k, v in extra_filters.items()])
        q = XFormSubmission.objects.filter(**extra_filters)
        tnum = 8
    else:
        q = XFormSubmission.objects
        tnum = 6
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum,
    }

    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T%d.id in %s' % (tnum, (str(tuple(location.get_children().values_list(\
                       'pk', flat=True)))))
    else:
        location_children_where = 'T%d.id = %d' % (tnum, location.get_children()[0].pk)

    return q.filter(
               xform__keyword=keyword,
               has_errors=False,
               created__lte=end_date,
               created__gte=start_date).values(
               'connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T%d.lft <= locations_location.lft' % tnum, \
                   'T%d.rght >= locations_location.rght' % tnum, \
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Count('id')).extra(order_by=['location_name'])


def total_attribute_value(attribute_slug, start_date, end_date, location, group_by_timespan=None):
    select = {
        'location_name':'T8.name',
        'location_id':'T8.id',
        'rght':'T8.rght',
        'lft':'T8.lft',
    }
    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T8.id in %s' % (str(tuple(location.get_children().values_list(\
                       'pk', flat=True))))
    else:
        location_children_where = 'T8.id = %d' % location.get_children()[0].pk
    return XFormSubmissionValue.objects.filter(
               submission__has_errors=False,
               attribute__slug=attribute_slug,
               submission__created__lte=end_date,
               submission__created__gte=start_date).values(
               'submission__connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T8.lft <= locations_location.lft',
                   'T8.rght >= locations_location.rght',
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Sum('value_int')).extra(order_by=['location_name'])


def reorganize_location(key, report, report_dict):
    for dict in report:
        location = dict['location_name']
        report_dict.setdefault(location, {'location_id':dict['location_id'], 'diff':(dict['rght'] - dict['lft'])})
        report_dict[location][key] = dict['value']


def flatten_location_list(report_dict):
    toret = []
    for location_name, value_dict in report_dict.items():
        value_dict['location_name'] = location_name
        toret.append(value_dict)
    return toret


def reorganize_timespan(timespan, report, report_dict, location_list, request=None):
    for dict in report:
        time = dict[timespan]
        if timespan == 'month':
            time = datetime.datetime(int(dict['year']), int(time), 1)
        elif timespan == 'week':
            time = datetime.datetime(int(dict['year']), 1, 1) + datetime.timedelta(days=(int(time) * 7))
        elif timespan == 'quarter':
            time = datetime.datetime(int(dict['year']), int(time) * 3, 1)

        report_dict.setdefault(time, {})
        location = dict['location_name']
        report_dict[time][location] = dict['value']

        if not location in location_list:
            location_list.append(location)


def get_group_by(start_date, end_date):
    interval = end_date - start_date
    if interval <= datetime.timedelta(days=21):
        group_by = GROUP_BY_DAY
        prefix = 'day'
    elif datetime.timedelta(days=21) <= interval <= datetime.timedelta(days=90):
        group_by = GROUP_BY_WEEK
        prefix = 'week'
    elif datetime.timedelta(days=90) <= interval <= datetime.timedelta(days=270):
        group_by = GROUP_BY_MONTH
        prefix = 'month'
    else:
        group_by = GROUP_BY_QUARTER
        prefix = 'quarter'
    return {'group_by':group_by, 'group_by_name':prefix}

