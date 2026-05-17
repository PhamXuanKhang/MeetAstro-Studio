# Kịch bản demo tiếng Việt - Golden case

Tài liệu này dùng để ghi âm demo luồng ghi âm trực tiếp hoặc upload audio. Mục tiêu là tạo một cuộc họp khoảng 8 phút, dễ đọc, ít từ tiếng Anh, và có đủ tín hiệu để app hiển thị transcript, meeting note, action items, suggested status updates, rồi push sang Jira.

## Không đọc phần này khi ghi âm

Task có sẵn đã được seed trước trong Jira và Supabase:

- Chuẩn bị checklist onboarding khách hàng
- Kiểm tra lỗi webhook thanh toán
- Cập nhật trạng thái loading dashboard
- Soạn mẫu email chăm sóc khách hàng

Kỳ vọng AI nhận diện:

- Existing status update: "Kiểm tra lỗi webhook thanh toán" đã hoàn thành.
- Existing status update: "Cập nhật trạng thái loading dashboard" đã bắt đầu xử lý, ưu tiên cao, hạn thứ Sáu, có tiêu chí nghiệm thu rõ ràng.
- Existing status update: "Chuẩn bị checklist onboarding khách hàng" đang bị chặn vì thiếu thông tin từ đội triển khai.
- New action item thật sự: "Chuẩn bị ghi chú phát hành cho bản cập nhật khách hàng tháng Năm", ưu tiên trung bình.
- Không tạo task mới trùng với các task đã có sẵn.

Gợi ý quay demo:

1. Bắt đầu ở màn "Cuộc họp mới", chọn ghi âm trực tiếp.
2. Chỉ cần demo live transcript trong 1-2 phút đầu để thấy chữ nhả ổn định.
3. Sau đó có thể tua/đợi đến khi xử lý xong và mở màn Transcript, Meeting note, Review & Push Jira.
4. Khi đọc, nói chậm hơn bình thường một chút, mỗi lượt nói dài 2-4 câu.

## Đoạn hội thoại để đọc khi ghi âm

Minh: Chào Linh, mình bắt đầu buổi họp cập nhật công việc tuần này nhé. Mục tiêu hôm nay là rà lại các việc đang mở, xác nhận việc nào đã xong, việc nào đang bị vướng, và chốt thêm một việc mới cho bản cập nhật khách hàng tháng Năm.

Linh: Vâng, em đã chuẩn bị sẵn. Hôm nay mình sẽ đi qua bốn việc: lỗi thanh toán, màn hình tổng quan, quy trình chào đón khách hàng mới, và nội dung gửi cho khách hàng sau khi phát hành.

Minh: Trước hết là việc kiểm tra lỗi thông báo thanh toán tự động. Đây là việc cũ đã có trên bảng công việc, không phải việc mới. Tuần trước trạng thái của việc này là đang xử lý. Hôm nay tình hình thế nào?

Linh: Việc kiểm tra lỗi thông báo thanh toán tự động đã hoàn thành. Nguyên nhân là hệ thống ghi nhận cùng một mã giao dịch hai lần khi bên thanh toán gửi lại thông báo. Em đã bổ sung kiểm tra trùng mã giao dịch trước khi ghi dữ liệu, và đã chạy thử lại ba trường hợp lỗi cũ. Kết quả là không còn phát sinh giao dịch bị lặp nữa.

Minh: Vậy mình cập nhật trạng thái việc kiểm tra lỗi thông báo thanh toán tự động thành hoàn thành. Bằng chứng là đã xác định nguyên nhân, đã sửa phần kiểm tra trùng mã giao dịch, và đã chạy thử lại thành công. Có cần tạo thêm việc mới cho phần thanh toán không?

Linh: Tạm thời không cần. Nếu tuần sau lỗi lặp lại thì mình mở việc riêng. Còn hiện tại việc cũ này có thể đóng.

Minh: Tiếp theo là việc cập nhật trạng thái đang tải ở màn hình tổng quan. Việc này cũng là việc cũ đã có trên bảng công việc, không phải việc mới. Trạng thái hiện tại thế nào?

Linh: Việc cập nhật trạng thái đang tải ở màn hình tổng quan đã bắt đầu xử lý. Em đã rà lại luồng hiển thị và thấy người dùng đang bị chờ ở ba điểm: lúc mở màn hình, lúc lọc dữ liệu, và lúc làm mới dữ liệu sau khi có thay đổi. Phần thiết kế tạm đã có, nhưng em chưa ghép vào toàn bộ màn hình.

Minh: Vậy mình cập nhật trạng thái việc đó thành đang xử lý. Mình cũng nâng mức ưu tiên lên cao vì phần này ảnh hưởng trực tiếp đến cảm giác ổn định của sản phẩm khi demo. Hạn hoàn thành là thứ Sáu tuần này. Tiêu chí nghiệm thu gồm ba ý: khi mở màn hình phải có thông báo đang tải, khi lọc dữ liệu không bị trắng màn hình, và khi làm mới dữ liệu phải có phản hồi rõ ràng trong vòng một giây.

Linh: Em đồng ý. Em sẽ xử lý theo ba tiêu chí đó. Em cũng sẽ thêm thông báo ngắn nếu không có dữ liệu, để người dùng hiểu là danh sách đang rỗng chứ không phải hệ thống bị lỗi.

Minh: Phần này nhớ ghi rõ là cập nhật cho việc cũ, không tạo việc mới. Hôm nay chỉ cập nhật trạng thái, mức ưu tiên, hạn xử lý, và tiêu chí nghiệm thu cho việc đang có.

Linh: Vâng, em ghi nhận.

Minh: Bây giờ sang việc chuẩn bị danh sách kiểm tra cho quy trình chào đón khách hàng mới. Đây cũng là việc cũ. Tuần trước mình chưa hoàn tất vì còn thiếu thông tin từ đội triển khai. Hôm nay có tiến triển gì không?

Linh: Việc này đang bị chặn. Em đã soạn bản nháp gồm các bước tạo tài khoản, hướng dẫn người dùng đầu tiên, kiểm tra quyền truy cập, và gửi tài liệu hướng dẫn. Tuy nhiên em chưa thể chốt được vì đội triển khai chưa xác nhận phần phân quyền cho từng nhóm khách hàng.

Minh: Vậy mình cập nhật trạng thái việc chuẩn bị danh sách kiểm tra cho khách hàng mới thành bị chặn. Lý do là thiếu xác nhận về phân quyền từ đội triển khai. Khi nào có thông tin thì mình mới hoàn thiện được.

Linh: Đúng rồi. Em đã nhắn lại cho anh Huy bên triển khai. Nếu sáng mai có phản hồi thì em có thể hoàn thiện bản nháp ngay trong ngày mai.

Minh: Được. Mình không tạo thêm việc mới ở đây. Chỉ ghi lại bằng chứng là bản nháp đã có, nhưng chưa chốt được vì thiếu xác nhận phân quyền.

Linh: Vâng.

Minh: Tiếp theo là mẫu email chăm sóc khách hàng. Đây là việc cũ cuối cùng trong danh sách. Việc này đã làm đến đâu rồi?

Linh: Em đã viết nháp phần mở đầu và phần cảm ơn khách hàng, nhưng chưa xong phần hướng dẫn sử dụng tính năng mới. Em nghĩ việc này chưa nên đánh dấu hoàn thành.

Minh: Đồng ý. Vì hôm nay không có thay đổi rõ ràng về trạng thái nên mình không cần cập nhật nhiều. Chỉ cần ghi chú là chưa hoàn thành và sẽ quay lại sau khi có nội dung bản cập nhật tháng Năm.

Linh: Vâng, em sẽ quay lại phần đó sau khi thống nhất ghi chú phát hành.

Minh: Nhắc đến bản cập nhật tháng Năm, đây là việc mới thật sự trong buổi họp hôm nay. Mình cần chuẩn bị ghi chú phát hành cho bản cập nhật khách hàng tháng Năm. Nội dung cần nói rõ có gì mới, lỗi nào đã sửa, khách hàng cần làm gì sau khi cập nhật, và nếu cần hỗ trợ thì liên hệ kênh nào.

Linh: Em có thể nhận việc này. Em sẽ chuẩn bị bản nháp ghi chú phát hành cho khách hàng. Em nghĩ mức ưu tiên trung bình là hợp lý, vì việc này quan trọng cho truyền thông nhưng không chặn việc sửa lỗi hoặc phát hành sản phẩm.

Minh: Đồng ý, mức ưu tiên trung bình. Người phụ trách là Linh. Hạn bản nháp đầu tiên là chiều thứ Năm. Sau đó mình sẽ đọc lại và góp ý vào sáng thứ Sáu.

Linh: Để em nói lại cho rõ: việc mới là chuẩn bị ghi chú phát hành cho bản cập nhật khách hàng tháng Năm. Người phụ trách là Linh. Hạn bản nháp là chiều thứ Năm. Mức ưu tiên là trung bình. Nội dung gồm điểm mới, lỗi đã sửa, hướng dẫn sau cập nhật, và kênh hỗ trợ.

Minh: Chính xác. Việc này có thể đưa vào nhóm kế hoạch phát hành tháng Năm. Không cần tách thành quá nhiều việc nhỏ trong demo hôm nay, chỉ cần một việc rõ ràng là đủ.

Linh: Em cũng đề xuất trong ghi chú phát hành mình dùng ngôn ngữ đơn giản, tránh thuật ngữ kỹ thuật. Khách hàng chỉ cần hiểu thay đổi này giúp họ làm việc nhanh hơn và ít gặp lỗi hơn.

Minh: Ý đó tốt. Em đưa luôn vào phần tiêu chí hoàn thành: ghi chú phát hành phải dễ hiểu với người dùng không chuyên kỹ thuật, có cấu trúc ngắn gọn, và có danh sách thay đổi chính.

Linh: Em ghi nhận.

Minh: Bây giờ mình tổng kết lại để tránh nhầm. Thứ nhất, việc kiểm tra lỗi thông báo thanh toán tự động đã hoàn thành, không tạo việc mới. Thứ hai, việc cập nhật trạng thái đang tải ở màn hình tổng quan đã bắt đầu xử lý, ưu tiên cao, hạn thứ Sáu, và có ba tiêu chí nghiệm thu. Thứ ba, danh sách kiểm tra cho quy trình chào đón khách hàng mới đang bị chặn vì thiếu xác nhận phân quyền. Thứ tư, việc mới duy nhất là chuẩn bị ghi chú phát hành cho bản cập nhật khách hàng tháng Năm, giao cho Linh, ưu tiên trung bình, hạn bản nháp chiều thứ Năm.

Linh: Em xác nhận đúng như vậy. Với việc thanh toán thì có thể đóng. Với màn hình tổng quan thì em tiếp tục làm theo tiêu chí nghiệm thu. Với danh sách kiểm tra khách hàng mới thì em chờ phản hồi từ đội triển khai. Với ghi chú phát hành tháng Năm thì em bắt đầu soạn bản nháp ngay hôm nay.

Minh: Sau khi hệ thống tạo biên bản họp, mình sẽ kiểm tra lại bản ghi lời nói trước. Nếu phần tên người nói hoặc nội dung nào bị nghe nhầm thì mình sửa nhanh. Sau đó mình xem biên bản họp, duyệt các đầu việc, và chỉ đẩy những việc đã đúng sang bảng công việc chung.

Linh: Vâng, cách đó ổn. Như vậy mình vừa giữ được lịch sử cuộc họp, vừa tránh tạo trùng việc cũ trên bảng công việc chung.

Minh: Chính xác. Mục tiêu của demo hôm nay là cho thấy hệ thống nghe được tiếng Việt ổn định, tạo biên bản họp dễ đọc, phân biệt được việc mới và việc cũ, đồng thời đề xuất cập nhật trạng thái cho các việc đã có.

Minh: Cảm ơn Linh. Mình kết thúc buổi họp.
