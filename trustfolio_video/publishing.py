"""No social network writes exist in this foundation."""
from .contract import Blocked


def readiness():
    return {'enabled':False,'instagram_reels':'NOT_IMPLEMENTED',
            'facebook_reels':'NOT_IMPLEMENTED','youtube_shorts':'OAUTH_NOT_VERIFIED',
            'required':['reviewed MP4 and hash','explicit publishing approval',
                        'account identity and OAuth scopes','durable independent campaign ledger',
                        'uncertain-result reconciliation before retries']}


def publish(*args, **kwargs):
    raise Blocked('Publishing disabled in code; environment variables cannot enable it')
