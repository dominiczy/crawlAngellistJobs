# -*- coding: utf-8 -*-
from mail_txt import mail_func
import scrapy
from pprint import pprint
import json
import urllib
import ast
import pickle

class JobsSpider(scrapy.Spider):
    name = "jobs"
    
    start_urls = ['https://angel.co/login']
    job_listings_url = 'https://angel.co/job_listings/startup_ids'
    dict_name = 'Hongkong'
    dict_size = 40
    location_filter = 'tab=find&filter_data%5Blocations%5D%5B%5D=1644-Hong+Kong'
    browse_startup_url = 'https://angel.co/job_listings/browse_startups_table?'
    apply_url = "https://angel.co/talent_api/startups/"
    companyDict = {}
    
    def parse_TEST(self, response):
        print('---------TEST STUFF--------\n')
        respHtm = urllib.request.urlopen("file:job table test.html").read()
                
       
    # Login to Angellist
    def parse(self, response):
        token = response.css('input[name=authenticity_token]::attr(value)').extract_first()
        return [scrapy.FormRequest.from_response(response,
                    formid='new_user',
                    formdata={'utf8':'%E2%9C%93', 
                              'authenticity_token':token,
                              'login_only':'true',
                              'user[email]': 'USEREMAIL', 
                              'user[password': 'PASSWORD'
                              },
                    callback=self.after_login)]

  
    def after_login(self,response):
        # TODO cycle through pages and add filter by signal if too many pages
        #yield scrapy.Request(url=u, callback=self.parse_search_jobs)
        yield scrapy.Request(url=self.job_listings_url,
                             method='POST',
                             headers={'X-Requested-With': 'XMLHttpRequest',
                                      'Referer':'https://angel.co/jobs'},
                             body=self.location_filter,
                             callback=self.parse_search)
    
 
   
            
            
    # Fetch startup jobs from startup ids 
    def parse_search(self, response):
        print('----------RESPONSE----------')
        #pprint(response.body)
        # Build url below automatically from response (if they don't match it will return 404)
        respStr = response.body.decode("utf-8")

        # string to dict
        respDict = json.loads(respStr)
        
        respDict['startup_ids'] = respDict.pop('ids')
        respDict['listing_ids'] = respDict.pop('listing_ids')
        respDict.pop('network_search')
        respDict.pop('job_filter')
        respDict.pop('suggested_filters')
        respDict.pop('promotion_event_id')
        
        # split dictionary into multiple dictionary cause else link will be too long and return 404
        respDictLst = []
        item_nr = 0
        dict_nr = 0
        respDictLst.append({'startup_ids':[],'listing_ids':[]})
        for startup_id, listing_id in zip(respDict['startup_ids'], respDict['listing_ids']):
            respDictLst[dict_nr]['startup_ids'].append(startup_id)
            respDictLst[dict_nr]['listing_ids'].append(listing_id)
            item_nr = item_nr + 1
            if item_nr > self.dict_size:
                respDictLst.append({'startup_ids':[],'listing_ids':[]})
                dict_nr = dict_nr + 1
                item_nr = 0
        
        for respDict in respDictLst:
            # get listings in form above
            listingDict = dict(enumerate(respDict['listing_ids']))
            newlistingDict = {}
            for key, value in listingDict.items():
                newlistingDict['listing_ids['+str(key)+'][]'] = listingDict[key]    
            respDict.pop('listing_ids')
            respDict['startup_ids[]'] = respDict.pop('startup_ids')
            newjsondict ={**respDict, **newlistingDict}
                
            respUrl = urllib.parse.urlencode(newjsondict, doseq=True)
            print(respUrl)
            requestStr = self.browse_startup_url + respUrl
            
            
            yield scrapy.Request(url=requestStr, callback = self.parse_startups) 
          
   
        
    # Fetch individual companies from search
    def parse_startups(self,response):
        print('----------RESPONSE STARTUPS----------')
        respHtm = response.body.decode("utf-8")
        companyNames = scrapy.Selector(text=respHtm).xpath('//div[@class=" djl87 job_listings fbw9 browse_startups_table_row _a _jm"]/@data-name').extract()
        companyIds = scrapy.Selector(text=respHtm).xpath('//div[@class=" djl87 job_listings fbw9 browse_startups_table_row _a _jm"]/@data-id').extract()
        job_ids_all_str = scrapy.Selector(text=respHtm).xpath('//div[@class=" djl87 job_listings fbw9 browse_startups_table_row _a _jm"]/@data-listing-ids').extract()
        if len(companyNames) +  len(companyIds)  + len(job_ids_all_str) is not 3*len(companyIds):
            print('###### ERROR DIFFERENT LENGTHS, ids ', len(companyIds), ', names ', len(companyNames),', links ',len(companyLinks),', locations ', len(companyLocations), ', jobs ', len(job_ids_all_str))
            return
        # convert strings to actual lists
        job_ids_all = []
        for job_ids in job_ids_all_str:
            job_ids_all.append(ast.literal_eval(job_ids))
            
       
        # build dict of all companies with all jobs
        for name, ids, job_ids in zip(companyNames, companyIds, job_ids_all):
            xpath_ = '//div[@data-id="'+ids+'"]//div[@class="tag locations tiptip"]/@title'
            location = scrapy.Selector(text=respHtm).xpath(xpath_).extract_first()
            if location is None:
                location = ''
            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="link"]/a[@class="website-link"]/text()'
            link = scrapy.Selector(text=respHtm).xpath(xpath_).extract_first()

            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="description"]/text()'
            description = scrapy.Selector(text=respHtm).xpath(xpath_).extract_first()
            if description is None:
                description = ""
            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="details-row team"]//div[@class="person"]//div[@class="name"]/a/text()'
            founder = scrapy.Selector(text=respHtm).xpath(xpath_).extract_first()
            
            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="details-row jobs"]//div[@class="title"]/a/text()'
            job_titles = scrapy.Selector(text=respHtm).xpath(xpath_).extract()
            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="details-row jobs"]//div[@class="title"]/a/@href'
            job_links = scrapy.Selector(text=respHtm).xpath(xpath_).extract()
            xpath_ = '//div[@class="details details-'+ids+'"]//div[@class="details-row jobs"]//div[@class="tags"]/text()'
            job_tags = scrapy.Selector(text=respHtm).xpath(xpath_).extract()
            
            jobDict = {}
            for job_id, title, job_link, tags in zip(job_ids, job_titles, job_links, job_tags):
                # on first iteration build apply link to get contact
                if not jobDict:
                    applyUrl = self.apply_url+ids+'/job_application_details?matched_job_listings[]='+str(job_id)
                    yield scrapy.Request(url=applyUrl, callback=self.parse_apply, meta={'companyIds':ids})
                tags = (tags.strip()).split(" · ")
                jobDict[job_id] = {'title':title,
                                   'link':job_link,
                                   'tags':tags}
            self.companyDict[ids] =    {'name':name,
                                   'link':link,
                                   'location':location.strip(),
                                   'founder':founder,
                                   'description':description.strip().replace('\n', ''),
                                   'jobs':jobDict}
            
            
            
    # get contact name from application window
    def parse_apply(self,response):
        companyIds = response.meta['companyIds']
        # Get name person
        respStr = response.body.decode("utf-8")        
        # string to dict
        respDict = json.loads(respStr)
        contactName = respDict['job_listings'][0]['recruiting_contact']['name']
        self.companyDict[companyIds]['recruiter'] = contactName
        print(self.companyDict[companyIds])
        
        # save python object
        with open(self.dict_name+'_companyDict.pickle', 'wb') as handle:
            pickle.dump(self.companyDict, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        with open(self.dict_name+'_companyDict.json', 'w') as fp:
            json.dump(self.companyDict, fp)


    
   
