import os
import mysql.connector
from lxml import etree
import xml.etree.ElementTree as ET
import requests

# Database connection parameters
config = {
    'user': os.getenv('db_userid'),
    'password': os.getenv('db_password'),
    'host': os.getenv('db_host'),
    'database': os.getenv('db_database'),
    'port': os.getenv('db_port')
}
# SAP endpoint URL and credentials
sap_url = 'https://secure.nipex-ng.com/sap/bc/srt/rfc/sap/zsrm_supplier_list/400/zsrm_supplier_list/zsrm_supplier_list'
username = os.getenv('srm_username')
password = os.getenv('srm_password')

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(dictionary=True)

    # SQL JOIN query with constants
    query = """
    SELECT
        s.Bidder_Number AS BIDDER_NUMBER,
        s.suppuserid AS SUPPUSERID,
        s.SUP_ID AS SUP_ID,
        'NAPIMS-NipeX' AS SUP_NAME,
        'nipex@nipex.com.ng' AS SUP_EMAIL,
        '08033333333' AS SUP_PHONE,
        REPLACE(r.PROD_CODE, '.','_') AS PROD_CODE,
        IF(r.PROD_CODE = '9.99.99', 'COMBINED', p.PROD_DESC) AS PROD_DESC,
        ss.SUP_Status AS SUP_STATUS,
        ss.date_expiration AS DATE_EXPIRATION
    FROM
        tblsupplier AS s
    JOIN tblSupplierRecon AS r ON s.SUP_ID = r.SUP_ID
    LEFT JOIN tblproductcode AS p ON r.PROD_CODE = p.PROD_CODE AND r.PROD_CODE != '9.99.99'
    JOIN tblsupplierstatus AS ss ON s.SUP_ID = ss.SUP_ID
    ORDER BY r.SN;
    """
    cursor.execute(query)

    # Fetch all results
    final_data = cursor.fetchall()

finally:
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()

# Convert final_data to XML
root = etree.Element("CombinedData")
for row in final_data:
    entry = etree.SubElement(root, "item")
    for key, value in row.items():
        child = etree.SubElement(entry, key)
        child.text = str(value)

xml_str = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
# #test to see what kind of data is generated
# with open("test_data1.xml", "wb") as xml_file:
#     xml_file.write(xml_str)

# Parse the original XML
root = ET.fromstring(xml_str)
extracted_data = root.find('.').findall('*')  # Extracting the nested XML elements

# Create the new XML structure
envelope = ET.Element("soap:Envelope", {
    "xmlns:soap": "http://www.w3.org/2003/05/soap-envelope",
    "xmlns:urn": "urn:sap-com:document:sap:rfc:functions"
})
header = ET.SubElement(envelope, "soap:Header")
body = ET.SubElement(envelope, "soap:Body")
supplier_list = ET.SubElement(body, "urn:ZSRM_SUPPLIER_LIST_PROD")
itab = ET.SubElement(supplier_list, "IT_ITAB")

# Append the extracted XML data to the new IT_ITAB element
for element in extracted_data:
    itab.append(element)

# Convert the new XML structure to a string
xml_data = ET.tostring(envelope, encoding='utf-8', method='xml').decode('utf-8')


# Add the XML declaration manually
xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data

# Headers
headers = {'Content-Type': 'application/soap+xml',}

# Function to post XML data to SAP
def post_xml_to_sap():
    try:
        response = requests.post(sap_url, data=xml_data, headers=headers, auth=(username, password))
        
        if response.status_code == 200:
            print("Request successful")
            # print("Response:", response.text)
        else:
            print(f"Request failed with status code {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"An error occurred: {e}")

# Post the XML data
post_xml_to_sap()



