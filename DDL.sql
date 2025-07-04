

CREATE DATABASE IF NOT EXISTS LMS;
USE LMS;


CREATE TABLE Person (
  personID           VARCHAR(20)                 NOT NULL PRIMARY KEY,
  fname              VARCHAR(50)                 NOT NULL,
  lname              VARCHAR(50)                 NOT NULL,
  personalEmail      VARCHAR(100),
  institutionalEmail VARCHAR(100)                NOT NULL UNIQUE,
  CNIC               VARCHAR(15)                 NOT NULL,
  gender             ENUM('M','F','O')           NOT NULL,
  DOB                DATE                        NOT NULL,
  cNumber            VARCHAR(15)                 NOT NULL,
  type               ENUM('Admin','Faculty','Student') NOT NULL
);





CREATE TABLE Admin (
  employeeID     VARCHAR(20)    NOT NULL PRIMARY KEY,
  joiningDate    DATE           NOT NULL,
  leavingDate    DATE,
  officeLocation VARCHAR(100),
  CONSTRAINT fk_admin_person
    FOREIGN KEY (employeeID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT chk_admin_dates
    CHECK (leavingDate IS NULL OR leavingDate >= joiningDate)
);




CREATE TABLE Department (
  departmentID   INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  departmentName VARCHAR(50)     NOT NULL,
  HOD            VARCHAR(20)     NULL
);





CREATE TABLE Program (
  programID      VARCHAR(10)       NOT NULL PRIMARY KEY,
  programName    VARCHAR(50)      NOT NULL,
  totalSemesters INT               NOT NULL,
  departmentID   INT               NOT NULL,
  CONSTRAINT fk_program_department
    FOREIGN KEY (departmentID)
    REFERENCES Department(departmentID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
);





CREATE TABLE Semester (
  semesterID INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  programID  VARCHAR(10)     NOT NULL,
  fee        DECIMAL(10,2),
  semesterNo INT             NOT NULL,
  CONSTRAINT fk_semester_program
    FOREIGN KEY (programID)
    REFERENCES Program(programID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT chk_semester_no
    CHECK (semesterNo >= 1 AND semesterNo < 10)
);





CREATE TABLE Course (
  courseCode   VARCHAR(20)       NOT NULL PRIMARY KEY,
  courseName   VARCHAR(50)      NOT NULL,
  creditHours  INT               NOT NULL,
  preRequisite VARCHAR(20)       NULL,
  programID    VARCHAR(10)       NOT NULL,
  description  TEXT,
  CONSTRAINT fk_course_prereq
    FOREIGN KEY (preRequisite)
    REFERENCES Course(courseCode)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT fk_course_program
    FOREIGN KEY (programID)
    REFERENCES Program(programID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
);





CREATE TABLE Class (
  classID   INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  programID VARCHAR(10)     NOT NULL,
  batchYear YEAR            NOT NULL,
  CONSTRAINT fk_class_program
    FOREIGN KEY (programID)
    REFERENCES Program(programID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
);





CREATE TABLE Faculty (
  employeeID   VARCHAR(20)       NOT NULL PRIMARY KEY,
  designation  VARCHAR(50)       NOT NULL,
  departmentID INT               NOT NULL,
  joiningDate  DATE              NOT NULL,
  CONSTRAINT fk_faculty_person
    FOREIGN KEY (employeeID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_faculty_department
    FOREIGN KEY (departmentID)
    REFERENCES Department(departmentID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
);





ALTER TABLE Department
  ADD CONSTRAINT fk_department_hod
    FOREIGN KEY (HOD)
    REFERENCES Faculty(employeeID)
    ON DELETE SET NULL
    ON UPDATE CASCADE;





CREATE TABLE Student (
  studentID VARCHAR(20)       NOT NULL PRIMARY KEY,
  classID   INT               NULL,
  programID VARCHAR(10)       NULL,
  status    ENUM('Enrolled','Graduated','Dropped') NOT NULL,
  CONSTRAINT fk_student_person
    FOREIGN KEY (studentID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_student_class
    FOREIGN KEY (classID)
    REFERENCES Class(classID)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT fk_student_program
    FOREIGN KEY (programID)
    REFERENCES Program(programID)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);






CREATE TABLE SemesterDetails (
  id         INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  semesterID INT             NOT NULL,
  courseCode VARCHAR(20)     NOT NULL,
  classID    INT             NOT NULL,
  session    VARCHAR(10),
  CONSTRAINT fk_sd_semester
    FOREIGN KEY (semesterID)
    REFERENCES Semester(semesterID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_sd_course
    FOREIGN KEY (courseCode)
    REFERENCES Course(courseCode)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT fk_sd_class
    FOREIGN KEY (classID)
    REFERENCES Class(classID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
 UNIQUE KEY uq_semesterDetails_unique (semesterID,courseCode,classID)
);






CREATE TABLE CourseAllocation (
  allocationID INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  teacherID    VARCHAR(20)     NOT NULL,
  courseCode   VARCHAR(20)     NOT NULL,
  session      VARCHAR(20),
  status       ENUM('Ongoing','Completed','Cancelled') DEFAULT 'Ongoing',
  CONSTRAINT fk_allocation_teacher
    FOREIGN KEY (teacherID)
    REFERENCES Faculty(employeeID)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT fk_allocation_course
    FOREIGN KEY (courseCode)
    REFERENCES Course(courseCode)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  UNIQUE KEY uq_allocation_unique (teacherID, courseCode, session)
);







CREATE TABLE Enrollment (
  enrollmentID   INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  studentID      VARCHAR(20)     NOT NULL,
  allocationID   INT             NOT NULL,
  enrollmentDate DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status         ENUM('Active','Dropped','Completed') DEFAULT 'Active',
  CONSTRAINT fk_enrollment_student
    FOREIGN KEY (studentID)
    REFERENCES Student(studentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_enrollment_allocation
    FOREIGN KEY (allocationID)
    REFERENCES CourseAllocation(allocationID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY uq_enrollment_unique (studentID, allocationID)
);







CREATE TABLE Assessment (
  assessmentID   INT                      NOT NULL PRIMARY KEY AUTO_INCREMENT,
  allocationID   INT                      NOT NULL,
  assessmentType ENUM('Quiz','Assignment','Midterm','Final') NOT NULL,
  assessmentName VARCHAR(20)		  NOT NULL,
  weightage      INT                      NOT NULL CHECK (weightage >= 0 AND weightage <= 100),
  assessmentDate DATE,
  totalMarks     INT                      NOT NULL,
  CONSTRAINT fk_assessment_allocation
    FOREIGN KEY (allocationID)
    REFERENCES CourseAllocation(allocationID)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);






CREATE TABLE Result (
  resultID     INT               NOT NULL PRIMARY KEY AUTO_INCREMENT,
  enrollmentID INT               NOT NULL UNIQUE,
  courseGPA    DECIMAL(4,2)      NOT NULL CHECK (courseGPA >= 0 AND courseGPA <= 4.00),
  CONSTRAINT fk_result_enrollment
    FOREIGN KEY (enrollmentID)
    REFERENCES Enrollment(enrollmentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);







CREATE TABLE AssessmentChecked (
  id           INT            NOT NULL PRIMARY KEY AUTO_INCREMENT,
  assessmentID INT            NOT NULL,
  enrollmentID INT            NOT NULL,
  resultID     INT            NOT NULL,
  obtained     DECIMAL(10,2)  NOT NULL CHECK (obtained >= 0),
  CONSTRAINT fk_ac_assessment
    FOREIGN KEY (assessmentID)
    REFERENCES Assessment(assessmentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_ac_enrollment
    FOREIGN KEY (enrollmentID)
    REFERENCES Enrollment(enrollmentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_ac_result
    FOREIGN KEY (resultID)
    REFERENCES Result(resultID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY uq_assessmentChecked (assessmentID,enrollmentID)
);







CREATE TABLE Transcript (
  id           INT           NOT NULL PRIMARY KEY AUTO_INCREMENT,
  studentID    VARCHAR(20)   NOT NULL,
  semesterID   INT           NOT NULL,
  totalCredits INT           NOT NULL,
  semesterGPA  DECIMAL(4,2)  NOT NULL CHECK (semesterGPA >= 0 AND semesterGPA <= 4.00),
  CONSTRAINT fk_transcript_student
    FOREIGN KEY (studentID)
    REFERENCES Student(studentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_transcript_semester
    FOREIGN KEY (semesterID)
    REFERENCES Semester(semesterID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY uq_transcript (studentID,semesterID)
);







CREATE TABLE Lecture (
  allocationID  INT         NOT NULL,
  lectureNo     INT         NOT NULL,
  lectureID     VARCHAR(10) NOT NULL PRIMARY KEY,   
  venue         VARCHAR(50) NOT NULL,
  startingTime  DATETIME    NOT NULL,
  endingTime    DATETIME    NOT NULL,
  topic         TEXT,

  CONSTRAINT fk_lecture_allocation
    FOREIGN KEY (allocationID)
    REFERENCES courseallocation(allocationID)
      ON DELETE CASCADE
      ON UPDATE CASCADE,
  CONSTRAINT chk_lecture_time
    CHECK (endingTime > startingTime)
);





CREATE TABLE Attendance (
  id             INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
  attendanceDate DATETIME      NOT NULL,
  studentID      VARCHAR(20)    NOT NULL,
  lectureID      VARCHAR(10)     NOT NULL,
  CONSTRAINT fk_attendance_student
    FOREIGN KEY (studentID)
    REFERENCES Student(studentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_attendance_lecture
    FOREIGN KEY (lectureID)
    REFERENCES Lecture(lectureID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
UNIQUE KEY uq_attendance (attendanceDate, studentID, lectureID)
);






CREATE TABLE Reviews (
  reviewID     INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  enrollmentID INT             NOT NULL,
  reviewText   TEXT            NOT NULL,
  createdAt    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reviews_enrollment
    FOREIGN KEY (enrollmentID)
    REFERENCES Enrollment(enrollmentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);






CREATE TABLE Alumni (
  alumniID       VARCHAR(20)     NOT NULL PRIMARY KEY,
  graduationDate DATE            NOT NULL,
  email          VARCHAR(100),
  employmentInfo TEXT,
  CONSTRAINT fk_alumni_student
    FOREIGN KEY (alumniID)
    REFERENCES Student(studentID)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);








CREATE TABLE Salary (
  salaryID    INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  employeeID  VARCHAR(20)     NOT NULL,
  year        SMALLINT        AS (YEAR(paymentDate)) STORED,
  month       TINYINT         NOT NULL CHECK (month BETWEEN 1 AND 12),
  amount      DECIMAL(10,2)   NOT NULL,
  paymentDate DATE            NOT NULL,
  CONSTRAINT fk_salary_employee
    FOREIGN KEY (employeeID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY uq_salary_unique (employeeID, year, month)
);






CREATE TABLE Qualification (
  qualificationID INT             NOT NULL PRIMARY KEY AUTO_INCREMENT,
  personID        VARCHAR(20)     NOT NULL,
  degreeTitle     VARCHAR(50)    NOT NULL,
  educationBoard  VARCHAR(20),
  institution     VARCHAR(50)    NOT NULL,
  passingYear     YEAR,
  totalMarks      INT,
  obtainedMarks   INT,
  isCurrent       BOOLEAN         DEFAULT FALSE,
  CONSTRAINT fk_qualification_person
    FOREIGN KEY (personID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT chk_marks
    CHECK (obtainedMarks IS NULL OR totalMarks IS NULL OR obtainedMarks <= totalMarks)
);






CREATE TABLE Address (
  personID      VARCHAR(20)     NOT NULL PRIMARY KEY,
  country       VARCHAR(50)     NOT NULL,
  province      VARCHAR(50),
  city          VARCHAR(50)     NOT NULL,
  zipCode       INT             NOT NULL,
  streetAddress VARCHAR(100),
  CONSTRAINT fk_address_person
    FOREIGN KEY (personID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);





CREATE TABLE AuditTrail (
  auditID    INT                     NOT NULL PRIMARY KEY AUTO_INCREMENT,
  userID     VARCHAR(20)             NOT NULL,
  actionType ENUM('CREATE','READ','UPDATE','DELETE','LOGIN','LOGOUT') NOT NULL,
  entityName VARCHAR(50)             NOT NULL,
  timeStamp  DATETIME                NOT NULL DEFAULT CURRENT_TIMESTAMP,
  IPaddress  VARCHAR(45)             NOT NULL,
  userAgent  VARCHAR(255)            NOT NULL,
  CONSTRAINT fk_audit_user
    FOREIGN KEY (userID)
    REFERENCES Person(personID)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  INDEX idx_audit_timestamp (timeStamp)
);









DELIMITER //

CREATE TRIGGER tr_Assessment_before_insert
BEFORE INSERT ON Assessment
FOR EACH ROW
BEGIN
  DECLARE current_sum INT;
  DECLARE error_msg VARCHAR(255);

  SELECT COALESCE(SUM(weightage), 0)
    INTO current_sum
    FROM Assessment
    WHERE allocationID = NEW.allocationID;

  IF current_sum + NEW.weightage > 100 THEN
    SET error_msg = CONCAT(
      'Total weightage for allocationID=', NEW.allocationID,
      ' cannot exceed 100. Existing=', current_sum,
      ', new=', NEW.weightage
    );
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = error_msg;
  END IF;
END//






CREATE TRIGGER tr_Assessment_before_update
BEFORE UPDATE ON Assessment
FOR EACH ROW
BEGIN
  DECLARE existing_sum INT;
  DECLARE error_msg VARCHAR(255);

  SELECT COALESCE(SUM(weightage), 0)
    INTO existing_sum
    FROM Assessment
    WHERE allocationID = OLD.allocationID
      AND assessmentID <> OLD.assessmentID;

  IF existing_sum + NEW.weightage > 100 THEN
    SET error_msg = CONCAT(
      'After update, total weightage for allocationID=', OLD.allocationID,
      ' would exceed 100. Sum(other rows)=', existing_sum,
      ', new=', NEW.weightage
    );
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = error_msg;
  END IF;
END//






CREATE TRIGGER tr_Lecture_before_insert
BEFORE INSERT ON Lecture
FOR EACH ROW
BEGIN
  DECLARE maxNo INT;
  SELECT COALESCE(MAX(lectureNo), 0)
    INTO maxNo
    FROM Lecture
    WHERE allocationID = NEW.allocationID;
  SET NEW.lectureNo = maxNo + 1;
  SET NEW.lectureID = CONCAT(NEW.allocationID, '-', LPAD(NEW.lectureNo, 2, '0'));
END;
//
DELIMITER ;




CREATE VIEW StudentSemesterTranscriptView AS
SELECT
  p.personID                   AS studentID,
  CONCAT(p.fname, ' ', p.lname) AS studentName,
  sem.semesterID               AS semesterID,
  sem.semesterNo               AS semesterNumber,
  sem.programID                AS programID,
  c.courseCode                 AS courseCode,
  c.courseName                 AS courseName,
  r.courseGPA                  AS courseGPA,
  t.totalCredits               AS semesterTotalCredits,
  t.semesterGPA                AS semesterGPA
FROM Student s
JOIN Person p
  ON s.studentID = p.personID
JOIN Enrollment e
  ON s.studentID = e.studentID
JOIN CourseAllocation ca
  ON e.allocationID = ca.allocationID
JOIN Course c
  ON ca.courseCode = c.courseCode
JOIN SemesterDetails sd
  ON sd.courseCode = c.courseCode
 AND sd.classID = s.classID
 AND sd.session = ca.session
JOIN Semester sem
  ON sd.semesterID = sem.semesterID
JOIN Result r
  ON r.enrollmentID = e.enrollmentID
JOIN Transcript t
  ON t.studentID = s.studentID
 AND t.semesterID = sem.semesterID;



CREATE VIEW CourseEnrollmentView AS
SELECT
  ca.allocationID,
  ca.courseCode,
  c.courseName,
  ca.session             AS courseSession,
  p.personID             AS studentID,
  CONCAT(p.fname, ' ', p.lname) AS studentName,
  e.enrollmentDate,
  e.status               AS enrollmentStatus
FROM Enrollment e
JOIN CourseAllocation ca
  ON e.allocationID = ca.allocationID
JOIN Course c
  ON ca.courseCode = c.courseCode
JOIN Student s
  ON e.studentID = s.studentID
JOIN Person p
  ON s.studentID = p.personID
ORDER BY
  ca.allocationID;



CREATE VIEW AttendanceSummaryView AS
SELECT
  s.studentID,
  CONCAT(p.fname, ' ', p.lname)   AS studentName,
  ca.allocationID,
  ca.courseCode,
  c.courseName,
  ca.session                       AS courseSession,
  COUNT(DISTINCT l.lectureID)      AS totalLecturesHeld,
  COUNT(a.attendanceDate)          AS lecturesAttended
FROM Attendance a
JOIN Lecture l
  ON a.lectureID = l.lectureID
JOIN Enrollment e
  ON a.studentID = e.studentID
  AND l.allocationID = e.allocationID
JOIN Student s
  ON e.studentID = s.studentID
JOIN Person p
  ON s.studentID = p.personID
JOIN CourseAllocation ca
  ON l.allocationID = ca.allocationID
JOIN Course c
  ON ca.courseCode = c.courseCode
GROUP BY
  ca.allocationID,
  s.studentID;



CREATE VIEW AssessmentResultView AS
SELECT
  ac.assessmentID,
  a.assessmentName,
  a.weightage,
  a.totalMarks               AS maxMarks,
  ac.obtained                AS marksObtained,
  ac.enrollmentID,
  s.studentID,
  CONCAT(p.fname, ' ', p.lname) AS studentName,
  ca.courseCode,
  c.courseName,
  ca.session             AS courseSession,
  r.courseGPA            AS finalGPA
FROM AssessmentChecked ac
JOIN Assessment a
  ON ac.assessmentID = a.assessmentID
JOIN Enrollment e
  ON ac.enrollmentID = e.enrollmentID
JOIN Student s
  ON e.studentID = s.studentID
JOIN Person p
  ON s.studentID = p.personID
JOIN CourseAllocation ca
  ON a.allocationID = ca.allocationID
JOIN Course c
  ON ca.courseCode = c.courseCode
LEFT JOIN Result r
  ON ac.enrollmentID = r.enrollmentID;



CREATE VIEW PayrollSummaryView AS
SELECT
  p.personID                            AS employeeID,
  CONCAT(p.fname, ' ', p.lname)         AS employeeName,
  YEAR(s.paymentDate)                   AS yearPaid,
  MONTH(s.paymentDate)                  AS monthPaid,
  s.amount                              AS salaryPaid,
  SUM(s.amount) OVER (
    PARTITION BY p.personID, YEAR(s.paymentDate)
  )                                      AS totalPaid,
  AVG(s.amount) OVER (
    PARTITION BY p.personID, YEAR(s.paymentDate)
  )                                      AS avgMonthPayment,
  COUNT(*) OVER (
    PARTITION BY p.personID, YEAR(s.paymentDate)
  )                                      AS monthsPaid
FROM Salary s
JOIN Person p
  ON s.employeeID = p.personID;

