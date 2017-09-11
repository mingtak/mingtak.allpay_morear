# -*- coding: utf-8 -*
from mingtak.allpay import _
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
#from zope.component import getMultiAdapter
from z3c.relationfield.relation import RelationValue
from zope.event import notify
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from plone import api
#from pyallpay import AllPay
from DateTime import DateTime
import random
import transaction
import json
import logging
import hashlib
import urllib
from Products.CMFPlone.utils import safe_unicode

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base


BASEMODEL = declarative_base()
# create_engine 內的字串，之後要改到 registry 讀取
ENGINE = create_engine('mysql+mysqldb://morear:morear@localhost/morear?charset=utf8', echo=True)


class ReturnUrl(BrowserView):
    """ Return URL
    """

    def __call__(self):
        context = self.context
        request = self.request
        response = request.response
        catalog = context.portal_catalog
        alsoProvides(request, IDisableCSRFProtection)

        itemInCart = request.cookies.get('itemInCart', '{}')

        with api.env.adopt_user(username="admin"):
            if not request.form['MerchantTradeNo']:
                return
            try:
                order = catalog({'Type':'Order', 'Title':request.form['MerchantTradeNo']})[0].getObject()
            except:
                return

            if not order.result:
                order.result = {}

            for key in request.form.keys():
                order.result[key] = request.form[key]

            return


class ClientBackUrl(BrowserView):
    """ Client back url
    """

    template = ViewPageTemplateFile("template/client_back_url.pt")
    def __call__(self):
        context = self.context
        request = self.request
        response = request.response
        catalog = context.portal_catalog
        portal = api.portal.get()

#        response.setCookie('itemInCart', '{}')
#        response.redirect('/logistics_map?MerchantTradeNo=%s' % request.form['MerchantTradeNo'])

        self.order = catalog({'Type':'Order', 'id':request.form['MerchantTradeNo']})[0]
        self.products = catalog({'Type':'Product', 'UID':self.order.productUIDs.keys()})
        if request.form.get('LogisticsType') == 'cvs':
            response.redirect('%s/logistics_map?MerchantTradeNo=%s&LogisticsType=%s&LogisticsSubType=%s' %
                (portal.absolute_url(), request.form.get('MerchantTradeNo'), request.form.get('LogisticsType'), request.form.get('LogisticsSubType'))
            )
            return

        # 計算佣金(聯盟行銷, 預設10%)
        self.orderTotal = self.order.getObject().amount
        if self.orderTotal:
            self.revenue = int(self.orderTotal * 0.10)
        else:
            self.revenue = 0

        self.traceCode = " \
            VA.remoteLoad({ \
                whiteLabel: { id: 8, siteId: 1193, domain: 'vbtrax.com' }, \
                conversion: true, \
                conversionData: { \
                    step: 'sale', \
                    revenue: '%s', \
                    orderTotal: '%s', \
                    order: '%s', \
                }, \
                locale: 'en-US', mkt: true \
            }); \
        " % (self.revenue, self.orderTotal, self.order.id)

        return self.template()


class CheckoutConfirm(BrowserView):
    """ Checkout Confirm
    """

    logger = logging.getLogger('bill.Checkout')
    template = ViewPageTemplateFile("template/checkout_confirm.pt")
    home_template = ViewPageTemplateFile("template/home_template.pt")
    cvs_template = ViewPageTemplateFile("template/cvs_template.pt")

    def get_home_template(self):
        return self.home_template()


    def get_cvs_template(self):
        return self.cvs_template()


    def __call__(self):
        context = self.context
        request = self.request
        response = request.response
        catalog = context.portal_catalog
        portal = api.portal.get()

        if api.user.is_anonymous():
            self.profile = None
#            response.redirect('/')
#            return
        else:
            currentId = api.user.get_current().getId()
            self.profile = portal['members'][currentId]

        self.itemInCart = request.cookies.get('itemInCart', '{}')
        self.itemInCart = json.loads(self.itemInCart)

        if not self.itemInCart:
            response.redirect(portal.absolute_url())
            return

        self.brain = catalog({'UID':self.itemInCart.keys()})

        self.shippingFee = 0
        self.discount = 0
        self.totalAmount = 0
        for item in self.brain:
            qty = self.itemInCart[item.UID]
            self.totalAmount += item.salePrice * qty
            self.shippingFee += item.standardShippingCost # 同品項只收一次運費(ex, item_1, qty=3, 運費也只收一筆)
            self.discount += (item.salePrice * item.maxUsedBonus * qty)

        if self.profile and self.discount > self.profile.bonus:
            self.discount = self.profile.bonus

        self.payable = self.totalAmount
        self.payable += self.shippingFee
        # 尚未減 discount , 放在 view 顯示

        return self.template()

# 會用到的先寫下來
#from hashlib import sha256
#from urllib import quote_plus

class Checkout(BrowserView):
    """ Checkout
    """
    prefixString = 'mingtak.allpay.browser.allpaySetting.IAllpaySetting'
    logger = logging.getLogger('bill.Checkout')

    def getCheckMacValue(self, payment_info):
        prefixString = self.prefixString

        hashKey = api.portal.get_registry_record('%s.checkoutHashKey' % prefixString)
        hashIv = api.portal.get_registry_record('%s.checkoutHashIV' % prefixString)

        sortedString = ''
        for k, v in sorted(payment_info.items()):
            sortedString += '%s=%s&' % (k, str(v))

        sortedString = 'HashKey=%s&%sHashIV=%s' % (str(hashKey), sortedString, str(hashIv))
        sortedString = urllib.quote_plus(sortedString).lower()
        checkMacValue = hashlib.sha256(sortedString).hexdigest()
        checkMacValue = checkMacValue.upper()
        return checkMacValue


    def __call__(self):
        context = self.context
        request = self.request
        response = request.response
        catalog = context.portal_catalog
        portal = api.portal.get()
        alsoProvides(request, IDisableCSRFProtection)

        if api.user.is_anonymous():
            request.response.redirect(portal.absolute_url())
            return

        prefixString = self.prefixString
#TODO: 要分離開，這個 itemInCart 要寫到外面去

        itemInCart = request.cookies.get('cart', '')
#        itemInCart = request.cookies.get('itemInCart', '')
        if not itemInCart:
            response.redirect(portal.absolute_url())

        itemInCart = json.loads(itemInCart)

        if api.user.is_anonymous():
            profile = None
        else:
            userId = api.user.get_current().getId()

#        import pdb; pdb.set_trace()
        itemUIDs = []
        for item in itemInCart:
            itemUIDs.append(item.keys()[0])

        brain = catalog({'UID':itemUIDs})
        totalAmount = 0
        itemName = ''
        itemDescription = ''
#        productUIDs = {}
        shippingFee = 0
        discount = 0
        specialDiscount = 0 # 未來促銷活動可用

        for item in itemInCart:
            item_uid = item.keys()[0]
            totalAmount += int(item.values()[0]['total'])
            qty = item.values()[0]['qty']
            unitPrice = item.values()[0]['price']
            itemTitle = catalog(UID=item_uid)[0].Title
#            import pdb;pdb.set_trace()
            itemName += '%s $%s X %s#' % (itemTitle, str(unitPrice), str(qty))

        orderInfo = request.form
        orderId = '%ss%s' % (DateTime().strftime('%Y%m%d%H%M%S'), random.randint(100,999))
        merchantTradeNo = orderId
        pickupType = 'onStore' if orderInfo['on_store'] else 'onDoor'

        if orderInfo['allday'] or ( orderInfo['morning'] and orderInfo['afternoon'] ):
            pickupTime = 'allday'
        else:
            pickupTime = 'morning' if orderInfo['morning'] else 'afternoon'

        pickupStoreUID = orderInfo.get('selected_store', 'null')
        b_name = orderInfo.get('buyerName', 'null')
        b_email = orderInfo.get('buyerEmail', 'null')
        b_phone = orderInfo.get('buyerPhone', 'null')
        b_city = orderInfo.get('buyerCity', 'null')
        b_addr = orderInfo.get('buyerAddr', 'null')

        r_name = orderInfo.get('receiverName', 'null')
        r_email = orderInfo.get('receiverEmail', 'null')
        r_phone = orderInfo.get('receiverPhone', 'null')
        r_city = orderInfo.get('receiverCity', 'null')
        r_addr = orderInfo.get('receiverAddr', 'null')

        i_2list = 1 if orderInfo.get('invoice2List') else 0
        i_invoiceNo = orderInfo.get('invoiceNo', 'null')
        i_invoiceTitle = orderInfo.get('invoiceTitle', 'null')
        i_city = orderInfo.get('invoiceCity', 'null')
        i_addr = orderInfo.get('invoiceAddr', 'null')
        conn = ENGINE.connect()

        # 建立訂單
        execStr = "INSERT INTO orderInfo(\
                       userId, orderId, pickupType, pickupTime, pickupStoreUID,\
                       b_name, b_email, b_phone, b_city, b_addr,\
                       r_name, r_email, r_phone, r_city, r_addr,\
                       i_2list, i_invoiceNo, i_invoiceTitle, i_city, i_addr)\
                   VALUES (\
                       '%s', '%s', '%s', '%s', '%s',\
                       '%s', '%s', '%s', '%s', '%s',\
                       '%s', '%s', '%s', '%s', '%s',\
                       %s, '%s', '%s', '%s', '%s');" %\
                     ( userId, orderId, pickupType, pickupTime, pickupStoreUID,\
                       b_name, b_email, b_phone, b_city, b_addr,\
                       r_name, r_email, r_phone, r_city, r_addr,\
                       i_2list, i_invoiceNo, i_invoiceTitle, i_city, i_addr )

        conn.execute(execStr)
#        import pdb; pdb.set_trace()

# 建立訂單內容品項, itemId 先保留不處理，待跟客戶確認訂單產品編號
        execStr = "INSERT INTO orderItem(orderId, p_UID, qty, unitPrice, parameterNo) VALUES"
        for item in itemInCart:
            uid = item.keys()[0]
            execStr += "( '%s', '%s', %s, %s, %s)," % (\
                orderId,
                uid,
                int(item[uid].get('qty', 1)),
                int(item[uid].get('price', 9999999)),
                int(item[uid].get('parameterNo', 0)),
            )

        execStr = execStr[:-1]
        conn.execute(execStr)
#        import pdb; pdb.set_trace()
        conn.close()

#        merchantTradeNo = '%ss%s' % (DateTime().strftime('%Y%m%d%H%M%S'), random.randint(1000,9999))

        """ order會用mysql作
        with api.env.adopt_roles(['Manager']):
            order = api.content.create(
                type='Order',
                title=merchantTradeNo,
                description = '%s, Total: $%s' % (itemDescription, totalAmount),
                productUIDs = itemInCart,
                amount = totalAmount,
                receiver = request.form.get('receiver', ''),
                phone = request.form.get('phone', ''),
                cellPhone = request.form.get('cellphone', ''),
                email = request.form.get('email',''),
                addr_city = request.form.get('city', ''),
                addr_district = request.form.get('district', ''),
                addr_zip = request.form.get('zipcode', ''),
                addr_address = request.form.get('address', ''),
                taxId = request.form.get('taxid', ''),
                invoiceTitle = request.form.get('invoice_title', ''),
                container=portal['resource']['order'],
            )
        """
        paymentInfoURL = api.portal.get_registry_record('%s.paymentInfoURL' % prefixString)
        clientBackURL = api.portal.get_registry_record('%s.clientBackURL' % prefixString)
        payment_info = {
            'MerchantTradeNo': merchantTradeNo,
            'ItemName': itemName,
            'TradeDesc': '%s, Total: $%s' % (itemDescription, totalAmount),
            'TotalAmount': totalAmount,
            'ChoosePayment': 'ALL',
            'PaymentType': 'aio',
            'EncryptType': 1,
            'PaymentInfoURL': paymentInfoURL,
            'ClientBackURL': '%s?MerchantTradeNo=%s&LogisticsType=%s&LogisticsSubType=%s' %
                (clientBackURL, merchantTradeNo,
                 request.form.get('LogisticsType', 'cvs'),
                 request.form.get('LogisticsSubType', 'UNIMART')),  #可以使用 get 帶參數
            'ReturnURL': api.portal.get_registry_record('%s.returnURL' % prefixString),
            'MerchantTradeDate': DateTime().strftime('%Y/%m/%d %H:%M:%S'),
            'MerchantID': api.portal.get_registry_record('%s.merchantID' % prefixString),
        }

        checkMacValue = self.getCheckMacValue(payment_info)
        payment_info['CheckMacValue'] = checkMacValue
        service_url = api.portal.get_registry_record('%s.aioCheckoutURL' % prefixString)
        form_html = self.gen_checkout_form(payment_info, service_url, True)
        response.setCookie('itemInCart', '{}')
        return form_html


    def gen_checkout_form(self, payment_info, service_url, auto_send=True):

        form_html = '<form id="allPay-Form" name="allPayForm" method="post" target="_self" action="%s" style="display: none;">' % service_url

        for i, val in enumerate(payment_info):
            print val, payment_info[val]
            form_html = "".join((form_html, "<input type='hidden' name='%s' value='%s' />" % (safe_unicode(val), safe_unicode(payment_info[val]))))

        form_html = "".join((form_html, '<input type="submit" class="large" id="payment-btn" value="BUY" /></form>'))
        if auto_send:
            form_html = "".join((form_html, "<script>document.allPayForm.submit();</script>"))
        return form_html
