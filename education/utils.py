from django.contrib.auth.models import User
from rapidsms_xforms.models import Xform, XformField, XformConstraint
from django.conf import settings

from poll.models import Poll
from script.models import Script, ScriptStep

try:
    from django.contrib.sites import Site
except ImportError:
    pass

XFORMS = ()
XFORM_FIELDS = {}

def init_structures(sender, **kwargs):
    pass


def init_xforms(sender, **kwargs):
    init_xforms_from_tuples(XFORMS, XFORM_FIELDS)


def init_autoreg(sender, **kwargs):
    script, created = Script.objects.get_or_create(
            slug="emis_autoreg", defaults={
            'name':"Education monitoring autoregistration script"})
    if created:
        user, created = User.objects.get_or_create(username="admin")

        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome to the SMS based school data collection pilot.The information you provide is valuable to improving the quality of education in Uganda.",
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=60,
        ))
        role_poll = Poll.objects.create(\
            name='emis_role', \
            user=user, type=Poll.TYPE_TEXT, \
            question='To register,tell us your role? Teacher, Head Teacher, SMC, GEM, CCT, DEO,or District Official.Reply with one of the roles listed.', \
            default_response=''
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=roll_poll,
            order=1,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        district_poll = Poll.objects.create(
            user=user, \
            type='district', \
            name='emis_district',
            question='What is the name of your district?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=district_poll,
            order=2,
            rule=ScriptStep.STRICT_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        county_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='emis_subcounty',
            question='What is the name of your sub county?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=county_poll,
            order=3,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        school1_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='emis_one_school',
            question='What is the name of your school?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=school1_poll,
            order=4,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        schoolmany_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='emis_many_school',
            question='Name the schools you are resonsible for.Separate each school name with a comma, for example "St. Mary Secondary,Pader Primary"', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=schoolmany_poll,
            order=5,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        name_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='emis_name',
            question='What is your name?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=name_poll,
            order=6,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=60,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome to the school monitoring pilot.The information you provide contributes to keeping children in school.",
            order=7,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=60,
            giveup_offset=0,
        ))

        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site = Site.objects.get_current()
            script.sites.add(site)


def init_scripts(sender, **kwargs):
    simple_scripts = [\
        (Poll.TYPE_NUMERIC, 'emis_abuse', 'How many abuse cases were recorded in the record book this month?'), \
        (Poll.TYPE_TEXT, 'emis_meals', 'How many children had meals at lunch today? Reply with ONE of the following - very few, less than half, more than half, very many'), \
        (Poll.TYPE_NUMERIC, 'emis_grant', 'How much of your annual capitation grant have you received this term? Reply with ONE of the following 25%, 50%, 75%% or 100%',), \
        #FIXME date type
        (Poll.TYPE_NUMERIC, 'emis_inspection', 'What date was your last school inspection?',), \
        #FIXME date type
        (Poll.TYPE_NUMERIC, 'emis_cct', 'What date was your last CCT visit?',), \
        # FIXME yesNo
        (Poll.TYPE_TEXT, 'emis_absence', 'Do you know if the head teacher was present at school today? Answer YES or NO', True), \
        (Poll.TYPE_TEXT, 'emis_smc_meals', 'How many children did you observe having a meal at lunch today, Reply with ONE of the following- very few, less than half, more than half, very many'), \
        # FIXME yesno
        (Poll.TYPE_TEXT, 'emis_grant_notice', 'Has UPE capitation grant been display on school notice board? Answer YES or NO', True), \
        # FIXME yesno
        (Poll.TYPE_TEXT, 'emis_inspection_yesno', 'Do you know if your school was inspected this term? Answer YES if there was inspection and NO if there was no inspection'),
        (Poll.TYPE_NUMERIC, 'emis_meetings', 'How many SMC meetings have you held this term?Give number of meetings held, if none, reply 0.'),
    ]
    user, created = User.objects.get_or_create(username='admin')
    for poll_info in simple_scripts:
        poll = Poll.objects.create(
            user=user, \
            type=poll_info[0], \
            name=poll_info[1],
            question=poll_info[2], \
            default_response='', \
        )
        if len(poll_info) > 3 and poll_info[3]:
            poll.add_yesno_categories()


def init_xforms_from_tuples(xforms, xform_fields):
    user = User.objects.get(username='admin')
    xform_dict = {}
    for keyword_prefix, keyword, separator, name, description in xforms:
        xform, created = XForm.objects.get_or_create(
            keyword=keyword,
            keyword_prefix=keyword_prefix,
            defaults={
                'name':name,
                'description':description,
                'response':'',
                'active':True,
                'owner':user,
                'site':Site.objects.get_current(),
                'separator':separator,
                'command_prefix':'',
            }
        )
        xform_dict["%s%s" % (keyword_prefix, keyword)] = xform

    for form_key, attributes in xform_fields.items():
        order = 0
        form = xform_dict[form_key]
        for command, field_type, description, required in attributes:
            xformfield, created = XFormField.objects.get_or_create(
                command=command,
                xform=form,
                defaults={
                    'order':order,
                    'field_type':field_type,
                    'type':field_type,
                    'name':description,
                    'description':description,
                }
            )
            if required:
                xformfieldconstraint, created = XFormFieldConstraint.objects.get_or_create(
                    field=xformfield,
                    defaults={
                        'type':'req_val',
                         'message':("Expected %s, none provided." % description)
                    }
            )
            order = order + 1
    return xform_dict
