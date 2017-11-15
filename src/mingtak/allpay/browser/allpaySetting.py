from mingtak.allpay import _
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from plone.z3cform import layout
from z3c.form import form
from plone.directives import form as Form
from zope import schema


class IAllpaySetting(Form.Schema):

    """ Basic setting for AllPay """
    merchantID = schema.TextLine(
        title=_(u"Merchant ID"),
        description=_(u"Merchant ID, for allPay"),
        required=True,
    )

    """ Checkout(cash flow) setting for AllPay """
    checkoutHashKey = schema.TextLine(
        title=_(u"Checkout Hash Key"),
        description=_(u"Checkout HashKey, for allPay"),
        required=True,
    )

    checkoutHashIV = schema.TextLine(
        title=_(u"Checkout Hash IV"),
        description=_(u"Checkout Hash IV, for allPay"),
        required=True,
    )

    aioCheckoutURL = schema.TextLine(
        title=_(u"All in one(AIO) Checkout Server URL"),
        description=_(u"aio server url, mapping to allpay aio server url"),
        required=True,
    )

    paymentInfoURL = schema.TextLine(
        title=_(u"Payment Info URL"),
        description=_(u"Payment info url."),
        required=True,
    )

    clientBackURL = schema.TextLine(
        title=_(u"Client Back URL"),
        description=_(u"Client back url."),
        required=True,
    )

    returnURL = schema.TextLine(
        title=_(u"Return URL"),
        description=_(u"Return url, for checkout."),
        required=True,
    )
    """ Checkout(cash flow) setting for AllPay """

    """ Logistics setting for AllPay """
    Form.mode(logisticsMapURL='hidden')
    logisticsMapURL = schema.TextLine(
        title=_(u"Logistics Map URL"),
        description=_(u"Logistics map url"),
        required=True,
    )

    Form.mode(logisticsExpressCreateURL='hidden')
    logisticsExpressCreateURL = schema.TextLine(
        title=_(u"Logistics Express Create URL"),
        description=_("Logistics express create url."),
    )

    Form.mode(logisticsHashKey='hidden')
    logisticsHashKey = schema.TextLine(
        title=_(u"Logistics Hash Key"),
        description=_(u"Logistics HashKey, for allPay"),
        required=True,
    )

    Form.mode(logisticsHashIV='hidden')
    logisticsHashIV = schema.TextLine(
        title=_(u"Logistics Hash IV"),
        description=_(u"Logistics Hash IV, for allPay"),
        required=True,
    )

    Form.mode(serverReplyURL='hidden')
    serverReplyURL = schema.TextLine(
        title=_(u"Server Reply URL, for MAP"),
        description=_(u"ServerReplyURL, for allPay's logistics"),
        required=True,
    )

    Form.mode(serverReplyURL_Express='hidden')
    serverReplyURL_Express = schema.TextLine(
        title=_(u"Server Reply URL, for Express Create"),
        description=_(u"ServerReplyURL, for allPay's logistics"),
        required=True,
    )

    Form.mode(clientReplyURL='hidden')
    clientReplyURL = schema.TextLine(
        title=_(u"Client Reply URL"),
        description=_(u"ClientReplyURL, for allPay's logistics"),
        required=True,
    )

    Form.mode(logisticsC2CReplyURL='hidden')
    logisticsC2CReplyURL = schema.TextLine(
        title=_(u"Logistics C2C Reply URL"),
        description=_(u"Logistics C2C Reply URL, for allPay's logistics"),
        required=True,
    )

    """ Logistics setting for AllPay """

    Form.mode(initialBonus='hidden')
    initialBonus = schema.Int(
        title=_(u"Initial Bonus Setting"),
        description=_(u"Initial Bonus Setting"),
        default=0,
        min=0,
    )


class AllpaySettingControlPanelForm(RegistryEditForm):
    form.extends(RegistryEditForm)
    schema = IAllpaySetting

AllpaySettingControlPanelView = layout.wrap_form(AllpaySettingControlPanelForm, ControlPanelFormWrapper)
AllpaySettingControlPanelView.label = _(u"Allpay Setting")

