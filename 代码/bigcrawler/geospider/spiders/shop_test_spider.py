# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
from scrapy_redis.spiders import RedisSpider
from scrapy import Spider
from geospider.ecommerce.spiderUtils.parser_util import get_html_with_request
from geospider.ecommerce.pageParser.shopping_itemsList_parser import analysis_method_selector, analysis_goods_list
from geospider.ecommerce.pageParser.shopping_navigation_parser import get_nav, get_searchUrl_and_keyword

from geospider.ecommerce.pageParser.selenium_batch_parser import \
    get_pageKeyDic, get_next_urlList_by_firstpage_url, get_all_page_number, \
    get_all_page_urls, get_pageKeyList, get_all_page_urls_by_pageKeyList, get_pageUrls_and_all_pageNumber

from geospider.ecommerce.pageParser.shopping_detail_parser import *
from urllib2 import quote
from geospider.items import Goods, Stores, Ecommerce
from bs4 import BeautifulSoup


class ShopKeywordSpider(RedisSpider):
    name = "shoptestspider"
    # allowed_domains = ["https://www.baidu.com"]
    start_urls = [
        'https://www.taobao.com/',
    ]
    redis_key = 'ecommerce:start_urls'
    def parse(self, response):

        # GOAL_KEYWORD_list = self.keywords
        GOAL_KEYWORD_list = [u'衣服']
        searchUrl_and_keyword = get_searchUrl_and_keyword(get_soup_by_html_source(response.text), response.url)
        print searchUrl_and_keyword
        if (searchUrl_and_keyword[0] == None):
            raise Exception('查询搜索URL失败')

        # 第一遍遍历
        goal_url = searchUrl_and_keyword[0]
        goal_key = searchUrl_and_keyword[1]
        goal_url_len = len(goal_url)

        goal_url_spilted = goal_url.split('&')
        key_index = 0
        simple_url = ""

        res_url_list = []
        res_key_list = []

        while key_index < len(goal_url_spilted):
            if (goal_key in goal_url_spilted[key_index]):
                # [:]左闭右开
                simple_url = ('&'.join(goal_url_spilted[:key_index + 1]))

                key_index += 1
                break
            key_index += 1
        # print goal_url
        original_html_len = len(get_html_with_request(goal_url))

        while (key_index < len(goal_url_spilted)):
            if (original_html_len <= len(get_html_with_request(simple_url))):
                break
            simple_url = simple_url + "&" + goal_url_spilted[key_index]
            key_index += 1
        for keyword in GOAL_KEYWORD_list:
            if keyword != None and keyword != '':
                searchKeywordValue = quote(keyword.encode('utf8'))
                item_list_url = simple_url.replace(goal_key, searchKeywordValue)
                # print item_list_url
                res_url_list.append(item_list_url)
                res_key_list.append(quote(keyword.encode('utf-8')))

        print res_url_list

        if (len(res_url_list) >= 1):
            page_list = []
            pageDict = None
            demo_url = None
            demo_key = None
            get_dict_attemps = 0
            pageKey_method = 0

            res_url_list_len = len(res_url_list)
            for index in range(0, res_url_list_len):
                # for test_url in res_url_list:
                test_url = res_url_list[index]
                print test_url

                page_list = get_next_urlList_by_firstpage_url(test_url)

                if (page_list == None):
                    # get_dict_attemps += 1
                    continue

                pageDict = get_pageKeyDic(page_list)

                if (pageDict == None or len(pageDict) == 0):
                    get_dict_attemps += 1
                    if (get_dict_attemps >= 2):
                        pageKey_method = 1
                        break
                    continue

                demo_url = test_url
                demo_key = res_key_list[index]
                break

            # pageKey_method = 0 使用pageKetDict解析翻页信息

            if (pageKey_method == 0):
                if (pageDict == None or page_list == None):
                    raise Exception("页面解析异常")

                print pageDict
                print page_list

                attached_1 = ""
                attached_2 = ""
                begin_index_p = -1
                tmp_url_len = min(len(page_list[1]), page_list[2])
                for url_len_p in range(0, tmp_url_len):
                    ch = page_list[1][url_len_p]
                    if (ch == '/' or ch == '&'):
                        begin_index_p = url_len_p

                    if (ch != page_list[2][url_len_p]):
                        attached_1 = page_list[1][begin_index_p:]
                        attached_2 = page_list[2][begin_index_p:]
                        # print attached_1
                        # print attached_2
                        break
                if (attached_1 == ""):
                    attached_1 = page_list[1].replace(demo_url, '')
                    attached_2 = page_list[2].replace(demo_url, '')

                for index in range(0, res_url_list_len):
                    # for goods_list_url in res_url_list:
                    goods_list_url = res_url_list[index]

                    if (goal_url_len != -1):
                        next_url1 = page_list[1].replace(demo_key, res_key_list[index])
                        next_url2 = page_list[2].replace(demo_key, res_key_list[index])
                    else:
                        next_url1 = goods_list_url + attached_1
                        next_url2 = goods_list_url + attached_2

                    # print next_url2
                    allnumber = get_all_page_number(goods_list_url)
                    print allnumber
                    # next_all_url_list = get_all_page_urls(pageKeyDic,page_list,allnumber)

                    res = get_all_page_urls(pageDict, [goods_list_url, next_url1, next_url2],
                                            allnumber)
                    """
                    每一个商品列表的分页信息

                    """
                    for each_goods_list_url in res:
                        yield Request(callback=self.goods_list_parse, url=each_goods_list_url)

            # pageKey_method = 1 使用 pageKeyList解析翻页信息
            else:
                pageKeyList = []
                page_list = []
                if (goal_url_len != -1):
                    for index in range(0, res_url_list_len):
                        test_url = res_url_list[index]
                        print test_url

                        page_list = get_next_urlList_by_firstpage_url(test_url)

                        if (page_list == None): continue

                        pageKeyList = get_pageKeyList(page_list)

                        if (pageKeyList == None or pageKeyList == []): continue
                        demo_url = test_url
                        demo_key = res_key_list[index]
                        break

                    for index in range(0, res_url_list_len):
                        # for goods_list_url in res_url_list:
                        goods_list_url = res_url_list[index]

                        next_url1 = page_list[1].replace(demo_key, res_key_list[index])
                        next_url2 = page_list[2].replace(demo_key, res_key_list[index])

                        # print next_url2
                        allnumber = get_all_page_number(goods_list_url)
                        print allnumber
                        # next_all_url_list = get_all_page_urls(pageKeyDic,page_list,allnumber)

                        res = get_all_page_urls_by_pageKeyList(pageKeyList, [goods_list_url, next_url1, next_url2],
                                                               allnumber)
                        for each_goods_list_url in res:
                            yield Request(callback=self.goods_list_parse, url=each_goods_list_url)
                else:

                    for test_url in res_url_list:
                        allnumber, page_list = get_pageUrls_and_all_pageNumber(test_url)
                        pageKeyList = get_pageKeyList(page_list)
                        res_url_list = []
                        if (pageKeyList != None and len(page_list) != 0):
                            goods_list_url = get_all_page_urls_by_pageKeyList(pageKeyList, page_list, allnumber)

                            for each_goods_list_url in goods_list_url:
                                yield Request(callback=self.goods_list_parse, url=each_goods_list_url)

    def goods_list_parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        analysis_method = analysis_method_selector(soup)

        analysis_res = analysis_goods_list(analysis_method, response.url, soup)

        if (analysis_method == 'JSON'):
            for each_item in analysis_res:
                each_detail_url = each_item['detail_url']
                item = Goods()

                item['title'] = each_item['title']
                item['price'] = each_item['price']
                item['pic_url'] = each_item['pic_url']
                item['detail_url'] = each_item['detail_url']
                item['taskid'] = str(self.name)

                # yield item

                yield Request(callback=self.goods_detail_parse, url=each_detail_url,
                              meta={'method': 'JSON', 'item': item}, )
        else:
            try:
                for each_detail_url in analysis_res:
                    yield Request(callback=self.goods_detail_parse, url=each_detail_url, meta={'method': 'OTHER'})

            except:

                pass

    def goods_detail_parse(self, response):
        method = response.meta['method']
        soup = BeautifulSoup(response.url, 'lxml')
        """
            如果上一个页面是用JSON解析的，那么这里就不需要再解析价格这些东西了
        """
        if (method != 'JSON'):
            goods_item = Goods()
            goods_dict = get_goods_dict_without_stroe(response.url)
            goods_item['price'] = goods_dict['price']
            goods_item['pic_url'] = goods_dict['pic_url']
            goods_item['detail_url'] = goods_dict['detail_url']

            goods_item['taskid'] = str(self.name)
        else:

            goods_item = response.meta['item']
            # yield item
        res_stroe_dic = get_store(soup, response.url)
        # 商品的评论采用店铺的评论
        try:
            goods_item['comment_degree'] = res_stroe_dic['comment_degree']
        except:
            goods_item['comment_degree'] = ""

        if (res_stroe_dic == None):
            store_item = Stores()
            store_item['name'] = ""
            store_item['store_url'] = ""
            store_item['comment_degree'] = ""
            store_item['taskid'] = str(self.name)
        else:

            # 构建店铺表
            store_item = Stores()
            store_item['name'] = res_stroe_dic['name']
            store_item['store_url'] = res_stroe_dic['store_url']
            store_item['comment_degree'] = res_stroe_dic['comment_degree']
            store_item['taskid'] = str(self.name)

        # 将两个表合起来
        res_item = Ecommerce()
        res_item['goods'] = goods_item
        res_item['stores'] = store_item

        yield res_item

    def stroe_detail_parse(self, respinse):
        pass