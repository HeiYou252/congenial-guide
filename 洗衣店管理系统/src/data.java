import java.sql.*;

public class ttt1 {
    public static void main(String[] args) {
        String dbURL = "jdbc:sqlserver://localhost:1433;DatabaseName=testDB;encrypt=true;trustServerCertificate=true";
        String userName = "U1";
        String userPwd = "111111";

        try (Connection dbConn = DriverManager.getConnection(dbURL, userName, userPwd);
             Statement stmt = dbConn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT * FROM stuff")) {

            System.out.println("连接数据库成功！");

            // 处理查询结果
            while (rs.next()) {
                String name = rs.getString("name");
                int age = rs.getInt("age");
                String description = rs.getString("description");
                System.out.println("姓名: " + name + ", 年龄: " + age + ", 描述: " + description);
            }

        } catch (SQLException e) {
            System.out.println("数据库操作失败: " + e.getMessage());
            e.printStackTrace();
        }
    }
}