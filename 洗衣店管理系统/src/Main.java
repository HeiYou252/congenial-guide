import java.sql.*;
import java.util.Scanner;

public class Main {
    // 数据库连接信息
    private static final String URL = "jdbc:sqlserver://localhost:1433;databaseName=LaundryDB;encrypt=true;trustServerCertificate=true";
    private static final String USER = "U1";
    private static final String PASSWORD = "111111";

    private static Connection conn;
    private static Scanner scanner = new Scanner(System.in);

    public static void main(String[] args) {
        System.out.println("=== 洗衣店管理系统 ===");

        try {
            // 连接数据库
            Class.forName("com.microsoft.sqlserver.jdbc.SQLServerDriver");
            conn = DriverManager.getConnection(URL, USER, PASSWORD);
            System.out.println("数据库连接成功！");

            // 主菜单
            while (true) {
                showMenu();
                int choice = scanner.nextInt();
                scanner.nextLine(); // 清除换行符

                switch (choice) {
                    case 1: receiveClothes(); break;
                    case 2: pickupClothes(); break;
                    case 3: queryOrder(); break;
                    case 4: showAllOrders(); break;
                    case 5: manageMembers(); break;
                    case 6: System.out.println("谢谢使用！"); return;
                    default: System.out.println("无效选择！");
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            try { if (conn != null) conn.close(); } catch (Exception e) {}
        }
    }

    private static void showMenu() {
        System.out.println("\n========== 主菜单 ==========");
        System.out.println("1. 收衣登记");
        System.out.println("2. 取衣处理");
        System.out.println("3. 查询订单");
        System.out.println("4. 查看所有订单");
        System.out.println("5. 会员管理");
        System.out.println("6. 退出系统");
        System.out.print("请选择操作: ");
    }

    // 1. 收衣登记
    private static void receiveClothes() throws SQLException {
        System.out.println("\n=== 收衣登记 ===");

        // 输入顾客信息
        System.out.print("请输入顾客电话: ");
        String phone = scanner.nextLine();

        // 查询顾客是否存在
        int customerId = findCustomer(phone);

        if (customerId == -1) {
            // 新顾客
            System.out.print("新顾客，请输入姓名: ");
            String name = scanner.nextLine();
            System.out.print("请输入地址: ");
            String address = scanner.nextLine();

            // 插入顾客
            String sql = "INSERT INTO Customer (CustName, CustPhone, CustAddress, RegDate) VALUES (?, ?, ?, GETDATE())";
            PreparedStatement pstmt = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            pstmt.setString(1, name);
            pstmt.setString(2, phone);
            pstmt.setString(3, address);
            pstmt.executeUpdate();

            ResultSet rs = pstmt.getGeneratedKeys();
            if (rs.next()) {
                customerId = rs.getInt(1);
            }
            pstmt.close();
            System.out.println("新顾客添加成功！");
        }

        // 输入衣物信息
        System.out.print("请输入衣物类型(西装/羽绒服/大衣/衬衫/裤子): ");
        String clothType = scanner.nextLine();
        System.out.print("请输入颜色: ");
        String color = scanner.nextLine();

        // 计算价格
        double price = calculatePrice(clothType);

        // 插入订单 - 使用方括号括住ORDER
        String sql = "INSERT INTO [Order] (CustID, CreateTime, TotalAmount, OrderStatus) VALUES (?, GETDATE(), ?, '已接收')";
        PreparedStatement pstmt = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
        pstmt.setInt(1, customerId);
        pstmt.setDouble(2, price);
        pstmt.executeUpdate();

        ResultSet rs = pstmt.getGeneratedKeys();
        int orderId = -1;
        if (rs.next()) {
            orderId = rs.getInt(1);
        }
        pstmt.close();

        // 插入衣物信息
        sql = "INSERT INTO Clothing (OrderID, ClothType, ClothColor, ReceiveDate, ExpectedDate) VALUES (?, ?, ?, GETDATE(), DATEADD(DAY, 3, GETDATE()))";
        pstmt = conn.prepareStatement(sql);
        pstmt.setInt(1, orderId);
        pstmt.setString(2, clothType);
        pstmt.setString(3, color);
        pstmt.executeUpdate();
        pstmt.close();

        System.out.println("收衣成功！订单号: " + orderId + ", 金额: " + price + "元");
    }

    // 2. 取衣处理
    private static void pickupClothes() throws SQLException {
        System.out.println("\n=== 取衣处理 ===");
        System.out.print("请输入订单号: ");
        int orderId = scanner.nextInt();
        scanner.nextLine();

        // 查询订单 - 使用方括号括住ORDER
        String sql = "SELECT o.*, c.CustName FROM [Order] o JOIN Customer c ON o.CustID = c.CustID WHERE o.OrderID = ?";
        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setInt(1, orderId);
        ResultSet rs = pstmt.executeQuery();

        if (!rs.next()) {
            System.out.println("订单不存在！");
            pstmt.close();
            return;
        }

        System.out.println("订单信息:");
        System.out.println("顾客: " + rs.getString("CustName"));
        System.out.println("金额: " + rs.getDouble("TotalAmount") + "元");
        System.out.println("状态: " + rs.getString("OrderStatus"));

        if (rs.getString("OrderStatus").equals("已取走")) {
            System.out.println("订单已完成，无需处理！");
            pstmt.close();
            return;
        }

        System.out.print("请输入实收金额: ");
        double paid = scanner.nextDouble();
        scanner.nextLine();

        double total = rs.getDouble("TotalAmount");
        if (paid < total) {
            System.out.println("支付金额不足！应付: " + total + "元");
            pstmt.close();
            return;
        }

        // 更新订单 - 使用方括号括住ORDER
        sql = "UPDATE [Order] SET PaidAmount = ?, IsPaid = 1, OrderStatus = '已取走' WHERE OrderID = ?";
        pstmt = conn.prepareStatement(sql);
        pstmt.setDouble(1, paid);
        pstmt.setInt(2, orderId);
        pstmt.executeUpdate();

        System.out.println("取衣成功！找零: " + (paid - total) + "元");
        pstmt.close();
    }

    // 3. 查询订单
    private static void queryOrder() throws SQLException {
        System.out.println("\n=== 查询订单 ===");
        System.out.print("请输入订单号: ");
        int orderId = scanner.nextInt();
        scanner.nextLine();

        // 使用方括号括住ORDER
        String sql = "SELECT o.*, c.CustName, cl.ClothType, cl.ClothColor " +
                "FROM [Order] o " +
                "JOIN Customer c ON o.CustID = c.CustID " +
                "JOIN Clothing cl ON o.OrderID = cl.OrderID " +
                "WHERE o.OrderID = ?";

        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setInt(1, orderId);
        ResultSet rs = pstmt.executeQuery();

        if (rs.next()) {
            System.out.println("\n订单信息:");
            System.out.println("订单号: " + orderId);
            System.out.println("顾客: " + rs.getString("CustName"));
            System.out.println("衣物: " + rs.getString("ClothType") + " " + rs.getString("ClothColor"));
            System.out.println("金额: " + rs.getDouble("TotalAmount") + "元");
            System.out.println("状态: " + rs.getString("OrderStatus"));
            System.out.println("创建时间: " + rs.getTimestamp("CreateTime"));
        } else {
            System.out.println("订单不存在！");
        }

        pstmt.close();
    }

    // 4. 查看所有订单
    private static void showAllOrders() throws SQLException {
        System.out.println("\n=== 所有订单 ===");

        // 使用方括号括住ORDER
        String sql = "SELECT o.OrderID, c.CustName, o.TotalAmount, o.OrderStatus, o.CreateTime " +
                "FROM [Order] o " +
                "JOIN Customer c ON o.CustID = c.CustID " +
                "ORDER BY o.CreateTime DESC";

        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(sql);

        System.out.println("订单号\t顾客\t\t金额\t状态\t\t创建时间");
        System.out.println("------------------------------------------------------------------------");

        while (rs.next()) {
            System.out.printf("%-8d%-12s%-8.2f%-10s%-20s%n",
                    rs.getInt("OrderID"),
                    rs.getString("CustName"),
                    rs.getDouble("TotalAmount"),
                    rs.getString("OrderStatus"),
                    rs.getTimestamp("CreateTime"));
        }

        stmt.close();
    }

    // 5. 会员管理
    private static void manageMembers() throws SQLException {
        System.out.println("\n=== 会员管理 ===");
        System.out.print("请输入顾客电话: ");
        String phone = scanner.nextLine();

        // 查询顾客
        String sql = "SELECT c.CustID, c.CustName, m.MemberLevel, m.Points " +
                "FROM Customer c " +
                "LEFT JOIN Member m ON c.CustID = m.CustID " +
                "WHERE c.CustPhone = ?";

        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setString(1, phone);
        ResultSet rs = pstmt.executeQuery();

        if (!rs.next()) {
            System.out.println("顾客不存在！");
            pstmt.close();
            return;
        }

        int custId = rs.getInt("CustID");
        String memberLevel = rs.getString("MemberLevel");

        if (memberLevel == null) {
            // 不是会员，询问是否注册
            System.out.print("该顾客不是会员，是否注册为会员？(y/n): ");
            String answer = scanner.nextLine();

            if (answer.equalsIgnoreCase("y")) {
                sql = "INSERT INTO Member (CustID, MemberLevel, Points, RegDate) VALUES (?, '普通', 0, GETDATE())";
                pstmt = conn.prepareStatement(sql);
                pstmt.setInt(1, custId);
                pstmt.executeUpdate();
                System.out.println("会员注册成功！");
            }
        } else {
            // 显示会员信息
            System.out.println("会员信息:");
            System.out.println("姓名: " + rs.getString("CustName"));
            System.out.println("等级: " + memberLevel);
            System.out.println("积分: " + rs.getInt("Points"));

            // 计算折扣
            double discount = getDiscount(memberLevel);
            System.out.println("折扣: " + (int)((1-discount)*100) + "折");
        }

        pstmt.close();
    }

    // 辅助方法：查找顾客
    private static int findCustomer(String phone) throws SQLException {
        String sql = "SELECT CustID FROM Customer WHERE CustPhone = ?";
        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setString(1, phone);
        ResultSet rs = pstmt.executeQuery();

        int customerId = -1;
        if (rs.next()) {
            customerId = rs.getInt("CustID");
        }

        pstmt.close();
        return customerId;
    }

    // 辅助方法：计算衣物价格
    private static double calculatePrice(String clothType) {
        switch (clothType) {
            case "西装": return 50.0;
            case "羽绒服": return 40.0;
            case "大衣": return 35.0;
            case "衬衫": return 15.0;
            case "裤子": return 20.0;
            default: return 25.0;
        }
    }

    // 辅助方法：获取会员折扣
    private static double getDiscount(String level) {
        if (level == null) return 1.0;

        switch (level) {
            case "钻石": return 0.8;
            case "金卡": return 0.85;
            case "银卡": return 0.9;
            case "普通": return 0.95;
            default: return 1.0;
        }
    }
}