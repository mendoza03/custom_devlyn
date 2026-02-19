{
    'name': "Biometric Attendance Machines Integration",
    'name_vi_VN': "Tích hợp Máy chấm công Sinh trắc học",
    'summary': """Integrate ZKTeco biometric attendance machines with Odoo to automate attendance tracking and efficiently manage HR data""",
    'summary_vi_VN': """Tích hợp máy chấm công sinh trắc học ZKTeco với Odoo, giúp tự động hóa quy trình điểm danh và quản lý dữ liệu nhân sự hiệu quả.""",
    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'live_test_url': "https://v18-biometric.demo.viindoo.cloud",
    'live_test_url_vi_VN': "https://v18-biometric.demo.viindoo.cloud",
    'demo_video_url': "https://www.youtube.com/watch?v=hR0cVYze0UE",
    'demo_video_url_vi_VN': "https://www.youtube.com/watch?v=8WwlgGZ4-_k",
    'website': 'https://viindoo.com/apps/app/18.0/to_attendance_device',
    'support': 'apps.support@viindoo.com',
    'category': 'Human Resources',
    'version': '1.1.7',

    'description': """
Demo video: `Biometric Attendance Machines Integration <https://www.youtube.com/watch?v=hR0cVYze0UE>`_

The module provides the capability to manage ZKTeco time attendance machines. Additionally, it allows for the management and synchronization of users and data from the time attendance machines to the HR management system.

Key Features
============

#. **Flexible Connection:**
    - Supports connecting attendance machines via IP or domain name, using TCP and UDP protocols.
#. **User Management on Attendance Machines:**
    - Delete users from the attendance machines.
    - Import users into the time attendance machine from employee data in Odoo.
    - Automatically map users on attendance machines with employee profiles in Odoo.
#. **Device Management:**
    - Support multiple ZKTeco attendance machines at different locations.
    - Support multiple time zones at various locations.
    - Support multiple attendance statuses (e.g., Check-in, Check-out, Start Overtime, End Overtime, etc.).
#. **Attendance Data:**
    - Automatically download attendance data from machines and synchronize it with the HR system in Odoo (users can configure automatic or manual synchronization).
    - Automatically clear attendance data from machines according to the configuration or manually clear it.
    - Permanently store attendance data in Odoo.
#. **Security:**
    - Authenticate and connect attendance machines with Odoo using passwords.
#. **Supported Devices:**
    - Supports various models of ZKTeco machines.
    - Fully tested with the following devices:
        - ZKTeco SENSEFACE 7A
        - RONALD JACK B3-C
        - ZKTeco K50
        - ZKTeco MA300
        - ZKTeco T4C
        - ZKTeco G3
        - RONALD JACK iClock260
        - ZKTeco K14
        - iFace702
        - Uface 800 (worked with finger and face)
        - ZKTeco K40
        - ZKTeco K20
        - ZKTeco U580
        - ZKTeco F18
        - ZKTeco F19
        - iFace402/ID
        - iFace800
        - iClock3000
        - iClock880-H
        - iclock 700​
        - Ronald Jack T8
        - Ronald jack 1000Plus
        - ZKTeco MB20
        - ZKteco IN0A-1
        - Uface 800
        - SpeedFace V5L
        - Speedface H5L(P)
        - VF680
        - RSP10k1
        - Uface 302
        - ... (please advise us your machines. Tks!)
    - Devices reported working by customers:
        - SpeedPalm-V5L
        - SenseFace 7
        - SenseFace 4
        - SenseFace 3
        - SenseFace 2A
        - MB series
        - F21
        - F22
        - SF400
        - uFace series
        - SilkBio series
        - IN05 & IN05-A
        - X628-C
        - U300-C
        - U260-C
        - iClock680
        - iClock360
        - UA series
        - WL series
        - P series
        - EFace10
        - ... (Support devices with ADMS feature)

Benefits
========
#. **Automated Attendance Process:** This module helps automate the process of downloading in/out data from the attendance machine to the system, minimizing manual work and errors in data entry.
#. **Data Synchronization:** Attendance data from the machine is synchronized with the human resource management system, ensuring consistency and accuracy of the data.
#. **User and Employee Management:** The module allows managing user information on the attendance machine and linking it with the employee list in the system, making it easy to track and manage.
#. **Reporting and Analysis:** Provides the ability to generate reports and analyze attendance data, giving businesses an overview of employee work patterns.
#. **Flexible Integration:** Supports multiple ZKTeco device models, allowing businesses to use existing devices without changing infrastructure.
#. **Enhanced Security:** Supports integration with various types of attendance machines, allowing businesses to use existing devices without changing infrastructure.
#. **Time and Cost Savings:** Automation and optimization of the attendance process help save time and costs for the business.

Who Should Use This Module?
===========================

#. If you want to automate the payroll process, consider using this module.
#. If you need stricter control over the attendance process, this module is the right choice.
#. If your company has a large number of employees, using this module will be very helpful.
#. If your company operates in multiple locations with different time zones, this module will help manage more efficiently.
#. If you want to store attendance data directly into your system, use this module.

Technical Requirement
======================
#. Requirement to install the Python library: setuptools
#. Please configure port forwarding (NAT) to point to your time attendance device

INTRODUCE ADSM ICLOUD FEATURE
=============================
Since Odoo 17, new feature was added call 'Icloud' to allow machine to push data into software. Before we only can get data from the machine, some client might get trouble when configure the machine because it need static IP and Modem configuration.
With this feature (optional, by default we still use either UDP or TCP one, we encourage to use this icloud option as the last one only because it has some security risk) you only need to configure in the machine by following instruction (this instruction use SpeedFace-H5L[P], but don't worry other machines have the same one):

* Go to 'Comm' setting of the machine
* Select Cloud Server Setting and you will see some configuration:

  * Enable Domain Nam: enable this if you going to use domain name
  * Server Address: enter ip address like 192.168.1.1 (check this by going to internet setting) or your domain name like example.viindoo.com
  * Server Port: If it hosted online, probably '443' is fine or any port that your server has. In the local environment it should be the port to run odoo config (8069 for example)
  * Enable Proxy Server (Some machines have): activate Proxy, after that you will need to specify Server IP and Port of the proxy one
  * HTTPS (Some machines have): Support https when pusing data, need to activate this unless you use local environment to develop. Note this, some machines might not have this, in that case it is necessary to change the nginx settings to prevent redirection to https for routers related to machines.
  * Then go to machine manager to create a new one with protocol 'icloud' , we have choose the best setting for you so you do not need to do that
  * Fill the 'Serial Number' (In the machine, go to 'System Info' -> 'Device Info' to see the Serial Number)
  * Hit button 'Upload Setting' to push setting into the machine
  * From now on, your machine is ready to push data into the software

Credit
======
Tons of thanks to Fananimi for his pyzk library @ https://github.com/fananimi/pyzk

We got inspired from that and customize it for more features (machine information, Python 3 support,
TCP/IP support, etc) then we integrated into Odoo by this great Attendance Machine application

Known Issue
===========

* To make this module work perfectly, your device will need to be available on internet (in case you use online platform like odoo.sh or self-hosted)
* Don't worry if the device is connected but still cannot download data, it could be one of following reason:

  * Wrong device mode (we support mode call 'Time Attendance' other mode like 'Access Control' will not work)
  * Lacking device configuration (by default some device will ignore the in/out checking stuff therefore we can not download your attendance data)

* Some device models may differ in firmware, communication protocols, or hardware configurations depending on the distribution region.

This module is developed and tested on the most common versions and may not be fully compatible with all variants.
To ensure successful implementation, please test it on the demo environment or contact us to verify compatibility.

Whatever the case is, you can always contact us at https://viindoo.com/ticket/team/8 for troubleshooting.

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

    """,
      'description_vi_VN': """
Demo video: `Tích hợp Máy chấm công Sinh trắc học <https://www.youtube.com/watch?v=8WwlgGZ4-_k>`_

Mô-đun này cung cấp khả năng quản lý máy chấm công sinh trắc học ZKTeco. Ngoài ra, nó cho phép quản lý và đồng bộ dữ liệu người dùng và dữ liệu từ máy chấm công vào hệ thống quản lý nhân sự.

Tính năng
=========

#. **Kết nối linh hoạt:**
    - Hỗ trợ kết nối máy chấm công qua IP hoặc tên miền, sử dụng giao thức TCP và UDP.
#. **Quản lý người dùng trên máy chấm công:**
    - Xóa người dùng trên máy chấm công.
    - Nhập người dùng vào máy chấm công từ dữ liệu nhân viên trong Odoo.
    - Tự động ánh xạ người dùng trên máy chấm công với hồ sơ nhân viên trong Odoo.
#. **Quản lý thiết bị:**
    - Hỗ trợ nhiều máy chấm công của hãng ZKTeco tại nhiều địa điểm khác nhau.
    - Hỗ trợ nhiều múi giờ tại nhiều địa điểm.
    - Hỗ trợ nhiều trạng thái điểm danh (ví dụ: Check-in, Check-out, Bắt đầu thêm giờ, Kết thúc thêm giờ, v.v.).
#. **Dữ liệu chấm công:**
    - Tự động tải dữ liệu chấm công từ máy chấm công và đồng bộ với hệ thống nhân sự trên Odoo (người dùng có thể cấu hình tự động hoặc chạy thủ công)
    - Tự động xóa dữ liệu chấm công trên máy chấm công theo cấu hình hoặc xóa thủ công.
    - Lưu dữ liệu chấm công vào Odoo vĩnh viễn.
#. **Bảo mật:**
    - Xác thực và kết nối máy chấm công với Odoo bằng mật khẩu.
#. **Thiết bị hỗ trợ:**
    - Hỗ trợ nhiều dòng máy của hãng ZKTeco
    - Đã được kiểm thử đầy đủ trên các thiết bị sau:
        - ZKTeco SENSEFACE 7A
        - RONALD JACK B3-C
        - ZKTeco K50
        - ZKTeco MA300
        - ZKTeco T4C
        - ZKTeco G3
        - RONALD JACK iClock260
        - ZKTeco K14
        - iFace702
        - Uface 800 (hoạt động trên cả vân tay và khuôn mặt)
        - ZKTeco K40
        - ZKTeco K20
        - ZKTeco U580
        - ZKTeco F18
        - ZKTeco F19
        - iFace402/ID
        - iFace800
        - iClock3000
        - iClock880-H
        - iclock 700​
        - Ronald Jack T8
        - Ronald jack 1000Plus
        - ZKTeco MB20
        - ZKteco IN0A-1
        - ZKTeco H5L
        - Uface 800
        - SpeedFace V5L
        - Speedface H5L(P)
        - VF680
        - RSP10k1
        - Uface 302
        - ... (vui lòng cung cấp thiết bị của bạn. Xin cảm ơn)
    - Thiết bị được khách hàng xác nhận hoạt động tốt:
        - SpeedPalm-V5L
        - SenseFace 7
        - SenseFace 4
        - SenseFace 3
        - SenseFace 2A
        - MB series
        - F21
        - F22
        - SF400
        - uFace series
        - SilkBio series
        - IN05 & IN05-A
        - X628-C
        - U300-C
        - U260-C
        - iClock680
        - iClock360
        - UA series
        - WL series
        - P series
        - EFace10
        - ... (Hỗ trợ các dòng máy có tính năng ADMS)

Lợi ích
=======

#. **Quy trình chấm công tự động:** Mô-đun này giúp tự động hóa quá trình tải dữ liệu vào/ra từ máy chấm công vào hệ thống, giảm thiểu công việc thủ công và sai sót trong nhập liệu.
#. **Đồng bộ dữ liệu:** Dữ liệu chấm công từ máy được đồng bộ với hệ thống quản lý nhân sự, đảm bảo tính nhất quán và độ chính xác của dữ liệu.
#. **Quản lý người dùng và nhân viên:** Mô-đun cho phép quản lý thông tin người dùng trên máy chấm công và liên kết với danh sách nhân viên trong hệ thống, giúp dễ dàng theo dõi và quản lý.
#. **Báo cáo và phân tích:** Cung cấp khả năng tạo báo cáo và phân tích dữ liệu chấm công, giúp doanh nghiệp có cái nhìn tổng quan về mô hình làm việc của nhân viên.
#. **Tích hợp linh hoạt:** Hỗ trợ nhiều dòng máy ZKTeco, cho phép doanh nghiệp sử dụng các thiết bị hiện có mà không cần thay đổi hạ tầng.
#. **Tăng cường bảo mật:** Hỗ trợ tích hợp với nhiều loại máy chấm công khác nhau, giúp doanh nghiệp sử dụng các thiết bị hiện có mà không cần thay đổi hạ tầng.
#. **Tiết kiệm thời gian và chi phí:** Tự động hóa và tối ưu hóa quy trình chấm công giúp doanh nghiệp tiết kiệm thời gian và chi phí.

Ai nên sử dụng module này
=========================

#. Nếu bạn muốn tự động hóa quy trình tính lương, hãy cân nhắc sử dụng mô-đun này.
#. Nếu bạn cần kiểm soát quy trình chấm công chặt chẽ hơn, mô-đun này là lựa chọn phù hợp.
#. Nếu doanh nghiệp của bạn có số lượng nhân viên lớn, việc sử dụng mô-đun này sẽ rất hữu ích.
#. Nếu doanh nghiệp của bạn hoạt động tại nhiều địa điểm với các múi giờ khác nhau, mô-đun này sẽ hỗ trợ quản lý hiệu quả hơn.
#. Nếu bạn muốn lưu trữ dữ liệu chấm công trực tiếp vào hệ thống của mình, hãy sử dụng mô-đun này.

Yêu cầu kỹ thuật
================
#. Yêu cầu cài đặt thư viện Python: setuptools
#. Vui lòng cấu hình chuyển tiếp cổng (NAT) để trỏ đến thiết bị chấm công của bạn

GIỚI THIỆU TÍNH NĂNG ADSM ICLOUD
================================
Kể từ Odoo 17, tính năng mới được thêm vào gọi là 'Icloud' để cho phép máy chấm cổng đẩy dữ liệu vào phần mềm. Trước đây chúng ta chỉ có thể lấy dữ liệu từ máy, một số khách hàng có thể gặp rắc rối khi cấu hình máy vì nó cần cấu hình IP tĩnh và Modem mạng.
Với tính năng này (tính năng tùy chọn, mặc định chúng tôi vẫn sử dụng giao thức UDP hoặc TCP, chúng tôi khuyến khích sử dụng tùy chọn icloud này làm phương án cuối cùng vì nó có một số rủi ro về bảo mật) bạn chỉ cần cấu hình trong máy theo hướng dẫn (hướng dẫn này hãy sử dụng SpeedFace-H5L[P], nhưng đừng lo các máy khác cũng có cơ chế tương tự):

* Vào cài đặt 'Comm' của máy
* Chọn Cloud Server Setting và bạn sẽ thấy một số cấu hình:

  * Enable Domain Name: kích hoạt tính năng này nếu bạn định sử dụng tên miền
  * Server Address: nhập địa chỉ IP như 192.168.1.1 (kiểm tra điều này bằng cách vào cài đặt internet) hoặc tên miền của bạn như example.viindoo.com
  * Server Port: Nếu nó được lưu trữ trực tuyến, có thể '443' hoặc bất kỳ cổng nào mà máy chủ của bạn có. Trong môi trường nội bộ, nó phải là cổng để chạy cấu hình odoo (ví dụ 8069)
  * Enable Proxy Server (Một số máy có): kích hoạt Proxy, sau đó bạn cần chỉ định IP Server và Port của proxy
  * HTTPS (Một số máy có): Hỗ trợ https khi đẩy dữ liệu, cần kích hoạt tính năng này trừ khi bạn sử dụng môi trường nội bộ để phát triển. Lưu ý điều này, một số máy có thể không có điều này, trong trường hợp đó cần phải thay đổi cài đặt nginx để ngăn chặn việc điều hướng sang https đối với các router liên quan đến máy chấm công.

  * Sau đó vào menu quán lý máy chấm công để tạo một cái mới với giao thức 'icloud', chúng tôi đã chọn cài đặt tốt nhất cho bạn nên bạn không cần phải làm gì cả
  * Điền "Sô sê ri" (Trong máy chấm công vào "System Info" -> "Device Info" để xem Số Sê ri)
  * Nhấn nút 'Upload Setting' để đẩy cài đặt vào máy chấm công
  * Từ nay máy của bạn đã sẵn sàng để đẩy dữ liệu vào phần mềm

Thông tin thêm
==============
Xin gửi lời cảm ơn chân thành đến Fananimi vì thư viện pyzk của anh ấy @ https://github.com/fananimi/pyzk

Chúng tôi đã lấy ý tưởng từ đó và tùy chỉnh để có nhiều tính năng hơn (thông tin thiết bị, hỗ trợ Python 3,
Hỗ trợ TCP / IP, v.v.) sau đó chúng tôi tích hợp vào Odoo bằng ứng dụng máy chấm công tuyệt vời này

Vấn đề đã biết
==============

* Để mô-đun này hoạt động hoàn hảo, thiết bị của bạn cần phải có kết nối internet (trong trường hợp bạn sử dụng nền tảng trực tuyến như odoo.sh hoặc tự thuể máy chủ)
* Đừng lo lắng nếu thiết bị đã kết nối nhưng vẫn không tải được dữ liệu, có thể là một trong những nguyên nhân sau:

  * Chế độ thiết bị sai (chúng tôi hỗ trợ gọi chế độ 'Time Attendance', chế độ khác như 'Access Control' sẽ không hoạt động)
  * Thiếu cấu hình thiết bị (mặc định một số thiết bị sẽ bỏ qua việc kiểm tra vào/ra nên chúng tôi không thể tải xuống dữ liệu vào/ra của bạn)

* Một số dòng thiết bị có thể có khác biệt về firmware, giao thức truyền thông hoặc cấu hình phần cứng tùy khu vực phân phối.

Module này được phát triển và kiểm thử trên các phiên bản phổ biến nhất và có thể không tương thích hoàn toàn với tất cả biến thể.
Để đảm bảo hiệu quả triển khai, vui lòng thử nghiệm trước trên hệ thống demo hoặc liên hệ để được xác nhận tính tương thích.

Dù thế nào đi nữa, bạn luôn có thể liên hệ với chúng tôi qua https://viindoo.com/vi/ticket/team/8 để giải quyết vấn đề.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'to_base'],

    'external_dependencies': {
        'python': ['setuptools'],
    },
    # always loaded
    'data': [
        'data/scheduler_data.xml',
        'data/attendance_state_data.xml',
        'data/mail_template_data.xml',
        'data/attendance_device_trans_flag_data.xml',
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'views/menu_view.xml',
        'views/attendance_device_views.xml',
        'views/attendance_state_views.xml',
        'views/attendance_device_location.xml',
        'views/device_user_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/user_attendance_views.xml',
        'views/attendance_activity_views.xml',
        'views/attendance_command_to_device_view.xml',
        'views/finger_template_views.xml',
        'wizard/employee_upload_wizard.xml',
        'wizard/device_confirm_wizard.xml',
        'views/bio_template_views.xml',
    ],
    'images': ['static/description/main_screenshot.gif'],
    'installable': True,
    'price': 198.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
