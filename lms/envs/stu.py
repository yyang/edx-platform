"""
This is the configuration file for STU production environment. It overrides 
layout settings in common.py .
"""

from .aws import *

PLATFORM_NAME = "MYSTU Learning"
CC_MERCHANT_NAME = PLATFORM_NAME
PLATFORM_TWITTER_ACCOUNT = "@mystu"
PLATFORM_FACEBOOK_ACCOUNT = "http://www.facebook.com/mystu"

COURSEWARE_ENABLED = True
ENABLE_JASMINE = False

####################### ORIGINAL FEATURES OVERRIDE #############################

FEATURES['USE_MICROSITES'] = True

# When True, all courses will be active, regardless of start date
FEATURES['DISABLE_START_DATES'] = True

# Enables the LMS bulk email feature for course staff
FEATURES['ENABLE_INSTRUCTOR_EMAIL'] = True

# If True and ENABLE_INSTRUCTOR_EMAIL: Forces email to be explicitly turned on
#   for each course via django-admin interface.
# If False and ENABLE_INSTRUCTOR_EMAIL: Email will be turned on by default
#   for all Mongo-backed courses.
FEATURES['REQUIRE_COURSE_EMAIL_AUTH'] = True

# Analytics experiments - shows instructor analytics tab in LMS instructor dashboard.
# Enabling this feature depends on installation of a separate analytics server.
FEATURES['ENABLE_INSTRUCTOR_ANALYTICS'] = False

# Toggle to indicate use of a custom theme
FEATURES['USE_CUSTOM_THEME'] = True
THEME_NAME = 'stu'

# Don't autoplay videos for students
FEATURES['AUTOPLAY_VIDEOS'] = True

# Toggle to enable certificates of courses on dashboard
FEATURES['ENABLE_VERIFIED_CERTIFICATES'] = True

# Toggle to enable chat availability (configured on a per-course
# basis in Studio)
FEATURES['ENABLE_CHAT'] = True

# Allow users to enroll with methods other than just honor code certificates
FEATURES['MULTIPLE_ENROLLMENT_ROLES'] = True

# Give course staff unrestricted access to grade downloads (if set to False
# only edX superusers can perform the downloads)
FEATURES['ALLOW_COURSE_STAFF_GRADE_DOWNLOADS'] = True

############################### DJANGO BUILT-INS ###############################

# CMS base
CMS_BASE = 'localhost:8001'

# Site info
SITE_ID = 1
SITE_NAME = "edxuat.stu.edu.cn"
HTTPS = 'on'
ROOT_URLCONF = 'lms.urls'

# Platform Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@stu.edu.cn'
DEFAULT_FEEDBACK_EMAIL = 'feedback@stu.edu.cn'
SERVER_EMAIL = 'edx-devops@stu.edu.cn'
TECH_SUPPORT_EMAIL = 'edx-technical@stu.edu.cn'
CONTACT_EMAIL = 'mystu@stu.edu.cn'
BUGS_EMAIL = TECH_SUPPORT_EMAIL
UNIVERSITY_EMAIL = 'info@stu.edu.cn'
PRESS_EMAIL = 'press@stu.edu.cn'
ADMINS = ()
MANAGERS = ADMINS

FAVICON_PATH = 'images/favicon.ico'

# Locale/Internationalization
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
TIME_ZONE = 'Asia/Shanghai'
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

############################### Pipeline #######################################
# !TODO: Read through original common.py and minimize number of requests;

############################## Video ###########################################
# !TODO: Gather update from Chengdu team and put information in it;

YOUTUBE = {
    # YouTube JavaScript API
    'API': 'www.youtube.com/iframe_api',

    # URL to test YouTube availability
    'TEST_URL': 'gdata.youtube.com/feeds/api/videos/',

    # Current youtube api for requesting transcripts.
    # For example: http://video.google.com/timedtext?lang=en&v=j_jEn79vS3g.
    'TEXT_API': {
        'url': 'video.google.com/timedtext',
        'params': {
            'lang': 'en',
            'v': 'set_youtube_id_of_11_symbols_here',
        },
    },
}

######################## CAS authentication ####################################
# !TODO: Gather information from YG;

if FEATURES.get('AUTH_USE_CAS'):
    CAS_SERVER_URL = 'https://provide_your_cas_url_here'
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'django_cas.backends.CASBackend',
    )
    INSTALLED_APPS += ('django_cas',)
    MIDDLEWARE_CLASSES += ('django_cas.middleware.CASMiddleware',)

########################## CERTIFICATE NAME ####################################

CERT_NAME_SHORT = "Certificate"
CERT_NAME_LONG = "Certificate of STU Course Achievement"

########################## Site Information Override ###########################

MICROSITE_CONFIGURATION = {
    "default": {
        "university": "Shantou University",
        "domain_prefix": "www",
        "platform_name": "Test Microsite",
        "logo_image_url": "test_microsite/images/header-logo.png",
        "email_from_address": "test_microsite@edx.org",
        "payment_support_email": "test_microsite@edx.org",
        "ENABLE_MKTG_SITE": False,
        "SITE_NAME": "test_microsite.localhost",
        "course_org_filter": "TestMicrositeX",
        "course_about_show_social_links": False,
        "css_overrides_file": "test_microsite/css/test_microsite.css",
        "show_partners": False,
        "show_homepage_promo_video": False,
        "course_index_overlay_text": "This is a Test Microsite Overlay Text.",
        "course_index_overlay_logo_file": "test_microsite/images/header-logo.png",
        "homepage_overlay_html": "<h1>This is a Test Microsite Overlay HTML</h1>"
    }
}
MICROSITE_ROOT_DIR = COMMON_ROOT + "/stu-site"