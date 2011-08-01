from django.db.models.signals import post_syncdb
from django.db import models
from rapidsms.models import Contact
from eav.models import Attribute
from script.signals import script_progress_was_completed, script_progress
from script.models import *
from rapidsms.contrib.locations.models import Location
from rapidsms_xforms.models import XFormField, XForm, XFormSubmission, dl_distance, xform_received
from uganda_common.utils import find_best_response, find_closest_match
from .utils import *
import re
import calendar
from django.conf import settings


class School(models.Model):
    name = models.CharField(max_length=160)
    emis_id = models.CharField(max_length=10)
    location = models.ForeignKey(Location)

    def __unicode__(self):
        return '%s' % self.name


class EmisReporter(Contact):
    school = models.ForeignKey(School, null=True)


def parse_date(command, value):
    return parse_date_value(value)


def parse_date_value(value):
    try:
        date_expr = re.compile(r"\d{1,2} (?:%s) \d{2,4}" % '|'.join(calendar.month_abbr[1:]))
        date_expr1 = re.compile(r"\d{1,2}-\d{1,2}-\d{2,4}")
        date_expr2 = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
        date_expr3 = re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}")
        date_expr4 = re.compile(r"\d{2,4}\.\d{1,2}\.\d{1,2}")
        date_expr5 = re.compile(r"\d{2,4}-\d{1,2}-\d{1,2}")

        if date_expr.match(value):
            dt_obj = datetime.strptime(date_str, "%d %b %Y")
        elif date_expr1.match(value):
            dt_obj = datetime.strptime(value, "%d-%m-%Y")
        elif date_expr2.match(value):
            dt_obj = datetime.strptime(value, "%d/%m/%Y")
        elif date_expr3.match(value):
            dt_obj = datetime.strptime(value, "%d.%m.%Y")
        elif date_expr4.match(value):
            dt_obj = datetime.strptime(value, "%Y.%m.%d")
        else:
            dt_obj = datetime.strptime(value, "%Y-%m-%d")

    except ValueError:
        raise ValidationError("Expected date format "
                "(\"dd mmm YYYY\", \"dd/mm/yyyy\", \"dd-mm-yyyy\", \"dd.mm.yyyy\", \"yyyy.mm.dd\" or \"yyyy-mm-dd\"), "
                "but instead received: %s." % value)

    time_tuple = dt_obj.timetuple()
    timestamp = time.mktime(time_tuple)
    return int(timestamp)


def parse_yesno(command, value):
    lvalue = value.lower().strip()
    if dl_distance(lvalue, 'yes') <= 1 or lvalue == 'y':
        return 1
    else:
        return 0


def emis_autoreg(**kwargs):

    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'emis_autoreg':
        return

    session = ScriptSession.objects.filter(script=progress.script, connection=connection).order_by('-end_time')[0]
    script = progress.script
    role_poll = script.steps.get(order=1).poll
    district_poll = script.steps.get(order=2).poll
    subcounty_poll = script.steps.get(order=3).poll
    school_poll = script.steps.get(order=4).poll
    schools_poll = script.steps.get(order=5).poll
    name_poll = script.steps.get(order=6).poll

    if not connection.contact:
            connection.contact = Contact.objects.create()
            connection.save
    contact = connection.contact

    role = find_best_response(session, role_poll)

    group = Group.objects.get(name='Other EMIS Reporters')
    default_group = group
    if role:
        group = find_closest_match(role, Group.objects)
        if not group:
            group = default_group
    contact.groups.add(default_group)


    subcounty = find_best_response(session, subcounty_poll)
    if subcounty:
        subcounty = find_closest_match(subcounty, Location.objects.filter(type__name='sub_county'))
        if subcounty:
            contact.reporting_location = subcounty

    name = find_best_response(session, name_poll)
    if name:
        name = ' '.join([n.capitalize() for n in name.lower().split(' ')])
        contact.name = name[:100]

    if not contact.name:
        contact.name = 'Anonymous User'
    contact.save()

    reporting_school = None
    school = find_best_response(session, schools_poll)
    if school:
        school_name = ' '.join([t.capitalize() for t in school.lower().split()])
        reporting_school = School.objects.get(name=school_name, \
                                            location__name=find_best_response(session, subounty_poll), \
                                            location__type='sub_county')

    EmisReporter.objects.create(pk=contact.pk, school=reporting_school)

    # Now that you have their roll, they should be signed up for the periodic polling
    _schedule_monthly_script(group, connection, 'emis_abuse', 'last', ['Teachers', 'Head Teachers'])
    _schedule_monthly_script(group, connection, 'emis_meals', 20, ['Teachers', 'Head Teachers'])
    _schedule_monthly_script(group, connection, 'emis_school_administrative', 15, ['Teachers', 'Head Teachers'])

    start_of_term = getattr(settings, 'SCHOOL_TERM_START', datetime.datetime.now())
    if group.name in ['Teachers', 'Head Teachers']:
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='emis_annual'))
        sp.set_time(start_of_term + datetime.timedelta(14))

    _schedule_monthly_script(group, connection, 'emis_smc_monthly', 28, ['SMC'])

    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    if group.name in ['SMC']:
        d = datetime.datetime.now()
        # get the date to a wednesday
        d = d + datetime.timedelta((2 - d.weekday()) % 7)
        in_holiday = True
        while in_holiday:
            in_holiday = False
            for start, end in holidays:
                if d >= start and d <= end:
                    in_holiday = True
                    break
            if in_holiday:
                d = d + datetime.timedelta(7)
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='emis_head teacher presence'))
        sp.set_time(d)


def _schedule_monthly_script(group, connection, script_slug, day_offset, role_names):
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    if group.name in role_names:
        d = datetime.datetime.now()
        day = calendar.mdays[d.month] if day_offset == 'last' else day_offset
        d = datetime.datetime(d.year, d.month, day)
        in_holiday = True
        while in_holiday:
            in_holiday = False
            for start, end in holidays:
                if d >= start and d <= end:
                    in_holiday = True
                    break
            if in_holiday:
                d = d + datetime.timedelta(31)
                day = calendar.mdays[d.month] if day_offset == 'last' else day_offset
                d = datetime.datetime(d.year, d.month, day)
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        sp.set_time(d)


def emis_reschedule_script(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    group = connection.contact.groups.all()[0]
    slug = progress.script.slug
    if not progress.script.slug.startswith('emis_'):
        return
    if slug == 'emis_abuse':
        _schedule_monthly_script(group, connection, 'emis_abuse', 'last', ['Teachers', 'Head Teachers'])
    elif slug == 'emis_meals':
        _schedule_monthly_script(group, connection, 'emis_meals', 20, ['Teachers', 'Head Teachers'])
    elif slug == 'emis_school_administrative':
        _schedule_monthly_script(group, connection, 'emis_school_administrative', 15, ['Teachers', 'Head Teachers'])
    elif slug == 'emis_annual':
        start_of_term = getattr(settings, 'SCHOOL_TERM_START', datetime.datetime.now())
        if group.name in ['Teachers', 'Head Teachers']:
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='emis_annual'))
            sp.set_time(start_of_term + datetime.timedelta(14))
    elif slug == 'emis_smc_monthly':
        _schedule_monthly_script(group, connection, 'emis_smc_monthly', 28, ['SMC'])
    elif slug == 'emis_head teacher presence':
        holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
        if group.name in ['SMC']:
            d = datetime.datetime.now()
            # get the date to a wednesday
            d = d + datetime.timedelta((2 - d.weekday()) % 7)
            in_holiday = True
            while in_holiday:
                in_holiday = False
                for start, end in holidays:
                    if d >= start and d <= end:
                        in_holiday = True
                        break
                if in_holiday:
                    d = d + datetime.timedelta(7)
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='emis_head teacher presence'))
            sp.set_time(d)


def emis_autoreg_transition(**kwargs):

    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'emis_autoreg':
        return
    script = progress.script
    session = ScriptSession.objects.filter(script=progress.script, connection=connection).order_by('-end_time')[0]
    role_poll = script.steps.get(order=1).poll
    role = find_best_response(session, role_poll)
    if role:
        group = find_closest_match(role, Group.objects)
    skipsteps = {
        'emis_subcounty':['Teachers', 'Head Teachers', 'SMC', 'GEM'],
        'emis_one_school':['Teachers', 'Head Teachers', 'SMC'],
        'emis_many_school':['GEM'],
    }
    skipped = True
    while skipped:
        skipped = False
        for step_name, roles in skipsteps.items():
            if  progress.step.poll and group and \
                progress.step.poll.name == step_name and role.name not in roles:
                skipped = True
                progress.step = progress.script.steps.get(order=progress.step.order + 1)
                progress.save()
                break

def xform_received_handler(sender, **kwargs):
    xform = kwargs['xform']
    submission = kwargs['submission']

    submission_day = getattr(settings, 'EMIS_SUBMISSION_WEEKDAY', 0)

    keywords = ['classrooms', 'classroomsused', 'latrines', 'latrinesused', 'deploy', 'enrolledb', 'enrolledg']
    if submission.has_errors:
        return

    sp = ScriptProgress.objects.filter(connection=submission.connection, script__slug='emis_annual').order_by('-time')
    if sp.count():
        sp = sp[0]
        if sp.step:
            for i in range(0, len(keywords)):
                if xform.keyword == keywords[i] and sp.step.order == i:
                    sp.status = 'C'
                    sp.save()
                    submission.response = "Thank you.  Your data on %s has been received" % xform.keyword
                    submission.save()
                    return

    elif xform.keyword in keywords:
        submission.response = "Please wait to send your data on %s until the appropriate time." % xform.keyword
        submission.has_errors = True
        submission.save()
        pass

    else:
        pass


Poll.register_poll_type('date', 'Date Response', parse_date_value, db_type=Attribute.TYPE_OBJECT)

XFormField.register_field_type('emisdate', 'Date', parse_date,
                               db_type=XFormField.TYPE_INT, xforms_type='integer')

XFormField.register_field_type('emisbool', 'YesNo', parse_date,
                               db_type=XFormField.TYPE_INT, xforms_type='integer')

post_syncdb.connect(init_structures, weak=True)
script_progress_was_completed.connect(emis_autoreg, weak=False)
script_progress_was_completed.connect(emis_reschedule_script, weak=False)
script_progress.connect(emis_autoreg_transition, weak=False)
xform_received.connect(xform_received_handler, weak=True)
