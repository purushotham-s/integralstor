from integralstor import command, alerts
import re, sys

def get_enclosure_devices():
    # Returns a list of /dev/sgX path for Connected Storage Enclosures
    enclosures = []
    try:
        sg_devs, err = command.get_command_output('sg_map -i')
        if err:
            raise Exception(err)

        if sg_devs:
            for sg_dev in sg_devs:
                    encl = re.findall('ENCL', sg_dev, re.IGNORECASE)
                    if encl:
                        res = re.findall(r'^\/\w+\/\w+', sg_dev)
                        if res:
                            enclosures += res
                    else:
                        raise Exception("No enclosures found")
    except Exception, e:
        return None, "Error retrieving enclosures : %s" % str(e)
    else:
        return enclosures, None

def get_psu_status():
    psu_status = {}
    try:
        encls, err = get_enclosure_devices()
        if err:
            raise Exception(err)

        if encls:
            for encl in encls:
                for psu in range(2):
                    tmp_cmd_output, err = command.get_command_output('sg_ses --index=ps,%d %s' % (psu, encl))
                    if err:
                        raise Exception(err)
                    if tmp_cmd_output:
                        for status_line in tmp_cmd_output:
                            result = re.findall(r'status: \w+', status_line)
                            if result:
                                psu_status['PSU-%d' % psu] = result[0]
    except Exception, e:
        return None, "Error retrieving JBOD PSU status : %s" % str(e)
    else:
        return psu_status, None

def main():
    try:
        vendor_info = 'N.A'
        product_info = 'N.A'
        psu_status, err = get_psu_status()
        if err:
            raise Exception(err)

        if psu_status:
            if 'status: Critical' in psu_status.values():
                alert_list = []
                for psu in psu_status:
                    if psu_status[psu] == 'status: Critical':
                        faulty_psu = psu
                encls, err = get_enclosure_devices()
                if err:
                    raise Exception(err)
                for encl in encls:
                    tmp_cmd_output, err = command.get_command_output('sginfo %s' % encl)
                    if err:
                        raise Exception(err)
                    for line in tmp_cmd_output:
                        vendor = re.findall(r'(^Vendor: *)(\w+)', line)
                        if vendor:
                            vendor_info = vendor[0][1]
                        product = re.findall(r'(^Product: *)(\w+)', line)
                        if product:
                            product_info = product[0][1]
                alert_str = '%s has gone down on %s %s' % (faulty_psu, vendor_info, product_info)
                alert_list.append({'subsystem_type_id': 5, 'severity_type_id': 3,
                                    'component': 'Power Supply', 'alert_str': alert_str})
                ret, err = alerts.record_alerts(alert_list)
                if err:
                    raise Exception(err)
    except Exception, e:
        return None, "Error recording PSU alert : %s" % str(e)

if __name__ == "__main__":
    ret = main()
    print ret
    if ret is not None:
        sys.exit(1)
    else:
        sys.exit(0)

#vim: tabstop=8 softtabstop=0 expandtab ai shiftwidth=4 smarttab
