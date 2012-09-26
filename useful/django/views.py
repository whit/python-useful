import os
import functools

from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext

from .crypto import SecretTokenGenerator


def page(template=None, **decorator_args):
    """
    Decorator to make template rendered by Django views dead simple.
    Takes the template path as first argument. See the code comments.
    Example::

        @page('payments/payments_info.html')
        def payment_info(request):
            return { ... context dict ... }
    """
    def page_decorator_wrapper(fn):
        @functools.wraps(fn)
        def page_decorator_inner_wrapper(request, *args, **kw):
            # Take the basic context dictionary from the optional decorator args.
            data = decorator_args.copy()

            # Call the original view.
            d = fn(request, *args, **kw)

            # Return now if it returned some kind of HTTP response itself, no job.
            if isinstance(d, HttpResponse):
                return d

            if d:
                data.update(d)

            # The view can override the template to use.
            template_name = data.get('template',  template)

            # By adding the debug_template parameter we switch to possible
            # debugging template:
            # payments/payments_info.html -> payments/payments_info_debug.html
            if settings.DEBUG and request.GET.get('debug_template'):
                stn = os.path.splitext(template_name)
                template_name = stn[0] + '_debug' + stn[1]

            # The view or the decorator call can override the context
            # instance. Otherwise, use the usual RequestContext.
            context_instance = data.get('context') or RequestContext(request)

            # Render the template.
            response = render_to_response(template_name, data, context_instance)
            return response

        return page_decorator_inner_wrapper
    return page_decorator_wrapper


class JsonResponse(HttpResponse):
    """
    Returns JSON encoded dict as HTTP response.
    """
    def __init__(self, response_dict, **kwargs):
        import json

        kwargs['content'] = json.dumps(response_dict, ensure_ascii=False)
        kwargs['mimetype'] = 'application/json'
        super(JsonResponse, self).__init__(**kwargs)


def protected_redirect(request):
    """
    Redirects to the URL in GET parameter u, but only if protection check passes.
    The 'u' GET parameter should be the target URL. The 't' should be the
    token created by SecretTokenGenerator().check_token(u).
    When the token check passes, the refreshing style redirection HTML page
    is returned. This is useful in hiding the true URL from where the link
    was clicked: The target site will get the redirector URL as referrer.
    """
    u, t = request.GET.get('u'), request.GET.get('t')
    if u and t and SecretTokenGenerator().check_token(u, t):
        return HttpResponse('''<html><head>
<meta http-equiv="refresh" content="1;url=http://%s">
</head>
<body>
    <a href="http://%s">Redirecting to %s</a>
    <script>window.location.replace("http://%s");
    </script>
</body></html>''' % (u, u, u, u))
    else:
        return HttpResponseBadRequest("Bad parameters or protection fault.")
