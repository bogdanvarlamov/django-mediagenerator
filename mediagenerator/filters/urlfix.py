import re
import os
from hashlib import sha1

from django.conf import settings

from mediagenerator import settings as appsettings
from mediagenerator.generators.bundles.base import FileFilter
from mediagenerator import utils

JS_URL_PREFIX = getattr(settings, "MEDIA_JS_URL_FILTER_PREFIX", r"OTA\.")


class UrlFixFilter(FileFilter):


    def get_dev_output(self, name, variation, content = None):

        if not content:
            content = super(UrlFixFilter, self).get_dev_output(name, variation)

        if name.startswith("admin-media"):
            return content



        rewriter = UrlRerwiter(name)
        return rewriter.rewrite(content)


class UrlRerwiter(object):

    re_css = re.compile(r'url\s*\((?P<d>["\'])?(?P<url>.*?)(?P=d)?\)', re.UNICODE)
    re_js = re.compile(r'OTA\.url\s*\((?P<d>["\'])(?P<url>.*?)(?P=d)\)', re.UNICODE)

    def __init__(self, name):
        self.name = name
        self.type = type
        self.root = settings.MEDIA_ROOT
        self.base = os.path.dirname(name)

        if name.endswith(".css"):
            self.type = "css"
        elif name.endswith(".scss"):
            self.type = "css"
        elif name.endswith(".js"):
            self.type = "js"
        else:
            raise Exception("Unsupported filetype for UrlFixFilter: %s" % name)

    def rewrite(self, content):
        if self.type == 'js':
            return self.re_js.sub(self._rewrite_js, content)
        else:
            return self.re_css.sub(self._rewrite_css, content)

    def _rewrite_css(self, match):
        url = match.group('url')
        if url.startswith("//") or url.startswith('data:image') or url.startswith("about:"):
            return "url(%s)" % url

        return "url(%s)" % self._rebase(url)

    def _rewrite_js(self, match):
        url = match.group('url')
        if url.startswith('//'):
            return "'%s'" % url

        return "'%s'" % self._rebase(url)

    def _rebase(self, url):

        if "#" in url:
            url, hashid = url.rsplit("#", 1)
            hashid = "#" + hashid
        else:
            hashid = ""

        if url.startswith("."):
            rebased = os.path.join(self.base, url)
            rebased = os.path.normpath(rebased)
        else:
            rebased = url.strip("/")

        local_file_path = utils.find_file(rebased)
        if not os.path.exists(local_file_path):
            print "Check path", os.path.realpath(local_file_path), rebased
            raise Exception("Unable to find url `%s` from file %s. File does not exists: %s" % (
                url,
                self.name,
                local_file_path
            ))
            
        if appsettings.MEDIA_DEV_MODE:
            prefix = appsettings.DEV_MEDIA_URL
            version = os.path.getmtime(local_file_path)
            rebased += "?v=%s" % version
        else:
            prefix = appsettings.PRODUCTION_MEDIA_URL
            with open(local_file_path, "rb") as sf:
                version = sha1(sf.read()).hexdigest()
                print(version)

            rebased_prefix, rebased_extention = rebased.rsplit(".", 1)
            rebased = "%s-%s.%s" % (rebased_prefix, version, rebased_extention)

        #need to correct the windows path (back slash) to web url (forward slash)
        rebased = "\"" + os.path.join(prefix, rebased.replace("\\", "/")) + "\""
        return rebased.strip("/") + hashid




