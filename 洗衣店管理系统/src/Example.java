import java.sql.*;
public class Example {
    public static void main(String[] args) {
        String dbURL = "jdbc:sqlserver://127.0.0.1:1433; DatabaseName=testDB;encrypt=true;trustServerCertificate=true";	// 连接字符串
        String userName = "U1";	String userPwd = "111111";

        try {
            Class.forName("com.microsoft.sqlserver.jdbc.SQLServerDriver");
            Connection dbConn = DriverManager.getConnection(dbURL, userName, userPwd);
            System.out.println("连接数据库成功");
            Statement stmt = dbConn.createStatement();
            //基本信息的录入
//            stmt.executeUpdate("INSERT INTO student VALUES('小明', '25', '80')");
//            stmt.executeUpdate("INSERT INTO student VALUES('小红', '16', '82')");
//            stmt.executeUpdate("INSERT INTO student VALUES('小黄', '27', '99')");
//            //学生成绩的修改
//            stmt.executeUpdate("UPDATE student SET grade = '80' WHERE name='小红'");
            //学生信息的删除
//            stmt.executeUpdate("DELETE FROM student WHERE name = '小明'");
            //学生成绩的查询
            ResultSet xs = stmt.executeQuery("SELECT * FROM student");
            while (xs.next()) {
                String name = xs.getString("name");
                int age = xs.getInt("age");
                String gra = xs.getString("grade");
                System.out.println(name + "\t" + age + "\t" + gra);
            }
        } catch (ClassNotFoundException | SQLException e) {
            e.printStackTrace();
            System.out.print("连接失败");
        }
    }
}